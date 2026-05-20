from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, TypeVar, Union

from somark._exceptions import InvalidParamError
from somark._models import ElementFormats, ExtractConfig, normalize_output_format
from somark._warnings import parse_max_concurrency


_FMT_MAP = {"md": "markdown", "zip": "zip", "json": "json"}
_VALID_API_FORMATS = {"markdown", "json", "zip"}
_VALID_FORMAT_HINT = "md, markdown, json, zip"

FileInput = Union[str, List[str]]
T = TypeVar("T")


@dataclass(frozen=True)
class ResolvedFileInputs:
    files: List[str]
    is_batch: bool


@dataclass(frozen=True)
class BatchRunResult:
    results: List[Any]
    warnings: List[str]
    concurrency: int


def build_parse_data(
    formats: Optional[List[str]] = None,
    element_formats: Optional[Union[ElementFormats, Dict[str, Any]]] = None,
    extract_config: Optional[Union[ExtractConfig, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {}
    if formats:
        mapped = [_FMT_MAP.get(normalize_output_format(f), normalize_output_format(f)) for f in formats]
        invalid = [f for f in mapped if f not in _VALID_API_FORMATS]
        if invalid:
            raise InvalidParamError(
                f"Unsupported output format: {', '.join(invalid)}. Valid formats: {_VALID_FORMAT_HINT}."
            )
        data["output_formats"] = mapped
    if element_formats:
        ef = element_formats if isinstance(element_formats, dict) else element_formats.model_dump()
        if ef:
            data["element_formats"] = json.dumps(ef)
    if extract_config:
        ec = extract_config if isinstance(extract_config, dict) else extract_config.model_dump()
        if ec:
            data["feature_config"] = json.dumps(ec)
    return data


def read_file_list(path: str) -> List[str]:
    manifest = Path(path)
    if not manifest.exists():
        raise InvalidParamError(f"File list not found: {path}")
    files: List[str] = []
    for line in manifest.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if not item:
            continue
        item_path = Path(item)
        files.append(str(item_path if item_path.is_absolute() else Path.cwd() / item_path))
    return files


def resolve_file_inputs(file: FileInput, file_list: bool = False) -> ResolvedFileInputs:
    if file_list:
        manifests = file if isinstance(file, list) else [file]
        files: List[str] = []
        for manifest in manifests:
            files.extend(read_file_list(manifest))
        return ResolvedFileInputs(files=files, is_batch=True)
    if isinstance(file, list):
        return ResolvedFileInputs(files=file, is_batch=True)
    return ResolvedFileInputs(files=[file], is_batch=False)


def resolve_cli_file_inputs(files: Sequence[str], file_list: Optional[str]) -> ResolvedFileInputs:
    resolved = list(files)
    if file_list:
        resolved.extend(read_file_list(file_list))
    return ResolvedFileInputs(files=resolved, is_batch=len(resolved) > 1 or file_list is not None)


def ensure_files_exist(files: Sequence[str]) -> None:
    missing = [file for file in files if not Path(file).is_file()]
    if missing:
        raise InvalidParamError("File not found: " + ", ".join(missing))


def parse_batch_settings(item_count: int) -> tuple[int, List[str]]:
    max_concurrency, warnings = parse_max_concurrency(os.environ.get("SOMARK_PARSE_MAX_CONCURRENCY"))
    return min(max_concurrency, item_count) or 1, warnings


def run_limited_sync(
    items: Sequence[str],
    worker: Callable[[str], T],
    on_result: Optional[Callable[[int, T], None]] = None,
) -> BatchRunResult:
    concurrency, warnings = parse_batch_settings(len(items))
    results: List[Any] = [None] * len(items)
    if concurrency <= 1:
        for index, item in enumerate(items):
            result = worker(item)
            results[index] = result
            if on_result:
                on_result(index, result)
        return BatchRunResult(results=results, warnings=warnings, concurrency=concurrency)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(worker, item): index for index, item in enumerate(items)}
        for future in as_completed(futures):
            index = futures[future]
            result = future.result()
            results[index] = result
            if on_result:
                on_result(index, result)
    return BatchRunResult(results=results, warnings=warnings, concurrency=concurrency)


async def run_limited_async(items: Sequence[str], worker: Callable[[str], Any]) -> BatchRunResult:
    import asyncio

    concurrency, warnings = parse_batch_settings(len(items))
    semaphore = asyncio.Semaphore(concurrency)

    async def run_one(index: int, item: str) -> tuple[int, Any]:
        async with semaphore:
            return index, await worker(item)

    pairs = await asyncio.gather(*[run_one(index, item) for index, item in enumerate(items)])
    results: List[Any] = [None] * len(items)
    for index, result in pairs:
        results[index] = result
    return BatchRunResult(results=results, warnings=warnings, concurrency=concurrency)


def attach_warnings(items: Sequence[Any], warnings: Sequence[str]) -> None:
    if not warnings:
        return
    for item in items:
        if isinstance(item, dict):
            item["warnings"] = list(item.get("warnings", [])) + list(warnings)
        else:
            existing = getattr(item, "warnings", [])
            item.warnings = list(existing) + list(warnings)
