from __future__ import annotations
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Literal, Dict, Any, Union, Callable, Awaitable
from somark._warnings import collect_api_warnings


@dataclass
class OutputTarget:
    format: str
    path: Optional[str] = None
    stdout: bool = False


@dataclass
class OutputPlan:
    formats: List[str]
    targets: List[OutputTarget]

    @property
    def stdout(self) -> bool:
        return len(self.targets) == 1 and self.targets[0].stdout


@dataclass
class SoMarkResponse:
    ok: bool
    code: int
    message: str
    warnings: List[str] = field(default_factory=list)

    def model_dump(self) -> dict:
        return asdict(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(ok={self.ok}, code={self.code}, message={self.message!r})"


@dataclass
class ExtractConfig:
    enable_text_cross_page: bool = False
    enable_table_cross_page: bool = False
    enable_title_level_recognition: bool = False
    enable_inline_image: bool = True
    enable_table_image: bool = True
    enable_image_understanding: bool = True
    keep_header_footer: bool = False

    def model_dump(self) -> dict:
        return asdict(self)


@dataclass
class ElementFormats:
    image: Optional[Literal["url", "base64", "file", "none"]] = None
    formula: Optional[Literal["latex", "mathml", "ascii"]] = None
    table: Optional[Literal["markdown", "html", "image"]] = None
    cs: Optional[Literal["image"]] = None

    def model_dump(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ParseResponse(SoMarkResponse):
    task_id: str = ""
    pages: int = 0
    file_type: str = ""
    imgs: List[str] = field(default_factory=list)
    md: Optional[str] = None
    json_output: Optional[Dict[str, Any]] = None
    zip_url: Optional[str] = None
    source_file_name: Optional[str] = None

    def save(self, path: str, format: Optional[Union[str, List[str]]] = None) -> None:
        """Save parsed output to file or to an existing directory."""
        target = os.fspath(path)
        plan = plan_output(self.source_file_name, target, format, allow_stdout=False)
        for output in plan.targets:
            if output.stdout or not output.path:
                raise ValueError("save path is required")
            self._save_format(output.path, output.format)

    def _save_format(self, path: str, format: str) -> None:
        fmt = normalize_output_format(format)
        if fmt == "zip":
            if not self.zip_url:
                raise ValueError("ZIP output URL was not returned by the API.")
            _download_output_file(path, self.zip_url)
            return
        _write_output_file(path, self._content_for_format(fmt))

    def _content_for_format(self, format: str) -> str:
        fmt = normalize_output_format(format)
        if fmt == "json":
            return json.dumps(self.json_output or {}, ensure_ascii=False, indent=2)
        if fmt == "md":
            return self.md or ""
        if fmt == "zip":
            if not self.zip_url:
                raise ValueError("ZIP output URL was not returned by the API.")
            return self.zip_url
        raise ValueError("Unsupported output format: {fmt}. Valid formats: md, markdown, json, zip.".format(fmt=fmt))

    @classmethod
    def from_api(cls, data: dict) -> "ParseResponse":
        # API response: {code, message, data: {task_id, metadata: {page_num, file_type}, result: {imgs, outputs: {markdown, json, zip}}}}
        api_data = data.get("data") or {}
        metadata = api_data.get("metadata") or {}
        result = api_data.get("result") or {}
        outputs = result.get("outputs") or {}
        warnings = collect_api_warnings(data)
        return cls(
            ok=data.get("code", -1) == 0,
            code=data.get("code", -1),
            message=data.get("message", data.get("msg", "")),
            warnings=warnings,
            task_id=api_data.get("task_id", ""),
            pages=metadata.get("page_num", 0),
            file_type=metadata.get("file_type", ""),
            imgs=result.get("imgs", []),
            md=outputs.get("markdown"),
            json_output=outputs.get("json"),
            zip_url=outputs.get("zip"),
            source_file_name=result.get("file_name") or api_data.get("file_name"),
        )


def normalize_output_format(format: str) -> str:
    fmt = format.strip().lower()
    return {"markdown": "md"}.get(fmt, fmt)


def normalize_save_formats(format: Optional[Union[str, List[str]]], path: Optional[str] = None) -> List[str]:
    if isinstance(format, list):
        raw_formats = format
    elif isinstance(format, str):
        raw_formats = [item.strip() for item in format.split(",")]
    else:
        ext = os.path.splitext(path or "")[1].lower().lstrip(".")
        raw_formats = [ext or "md"]
    formats = [normalize_output_format(item) for item in raw_formats if item.strip()]
    if not formats:
        formats = ["md"]
    invalid = [fmt for fmt in formats if fmt not in {"md", "json", "zip"}]
    if invalid:
        raise ValueError(
            "Unsupported output format: {fmt}. Valid formats: md, markdown, json, zip.".format(
                fmt=", ".join(invalid)
            )
        )
    return formats


def plan_output(
    source_file_name: Optional[str],
    out: Optional[str],
    format: Optional[Union[str, List[str]]] = None,
    *,
    allow_stdout: bool = False,
    batch: bool = False,
) -> OutputPlan:
    target = os.fspath(out) if out is not None else None
    formats = normalize_save_formats(format, target)
    if batch:
        if not target or not os.path.isdir(target):
            raise ValueError("batch parse requires --out to be an existing directory")
        return _directory_output_plan(source_file_name, target, formats)

    if not target:
        if len(formats) > 1:
            raise ValueError("multiple formats require --out to be an existing directory")
        if not allow_stdout:
            raise ValueError("output path is required")
        return OutputPlan(formats=formats, targets=[OutputTarget(format=formats[0], stdout=True)])

    if os.path.isdir(target):
        return _directory_output_plan(source_file_name, target, formats)
    if len(formats) > 1:
        raise ValueError("multiple formats require --out to be an existing directory")
    if _looks_like_directory_path(target):
        raise ValueError(f"output directory does not exist: {target}")
    parent = os.path.dirname(os.path.abspath(target)) or os.getcwd()
    if not os.path.isdir(parent):
        raise ValueError(f"output parent directory does not exist: {parent}")
    return OutputPlan(formats=formats, targets=[OutputTarget(format=formats[0], path=target)])


def _directory_output_plan(source_file_name: Optional[str], directory: str, formats: List[str]) -> OutputPlan:
    stem = _source_stem(source_file_name)
    if not stem:
        raise ValueError("saving to a directory requires a source file name")
    return OutputPlan(
        formats=formats,
        targets=[
            OutputTarget(format=fmt, path=os.path.join(directory, f"{stem}.{_format_ext(fmt)}")) for fmt in formats
        ],
    )


def _format_ext(format: str) -> str:
    return "md" if normalize_output_format(format) == "md" else normalize_output_format(format)


def _source_stem(file_name: Optional[str]) -> Optional[str]:
    if not file_name:
        return None
    return os.path.splitext(os.path.basename(file_name))[0]


def _looks_like_directory_path(path: str) -> bool:
    return path.endswith((os.sep, "/")) or (os.altsep is not None and path.endswith(os.altsep))


def _write_output_file(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _download_output_file(path: str, url: str) -> None:
    import httpx

    try:
        with httpx.stream("GET", url, follow_redirects=True, timeout=60.0) as response:
            response.raise_for_status()
            with open(path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
    except httpx.HTTPError as e:
        raise ValueError(f"failed to download ZIP output: {e}") from e


@dataclass
class Usage(SoMarkResponse):
    remaining_paid_pages: int = 0
    remaining_free_pages_today: int = 0
    remaining_free_pages_this_month: int = 0
    dashboard_url: str = "https://somark.tech/workbench"

    @classmethod
    def from_api(cls, data: dict) -> "Usage":
        api_data = data.get("data") or {}
        warnings = collect_api_warnings(data)
        return cls(
            ok=data.get("code", -1) == 0,
            code=data.get("code", -1),
            message=data.get("message", data.get("msg", "")),
            warnings=warnings,
            remaining_paid_pages=api_data.get("remaining_paid_pages", 0),
            remaining_free_pages_today=api_data.get("remaining_free_pages_today", 0),
            remaining_free_pages_this_month=api_data.get("remaining_free_pages_this_month", 0),
            dashboard_url=api_data.get("dashboard_url", "https://somark.tech/workbench"),
        )

    def __repr__(self) -> str:
        return (
            f"Usage(remaining_paid_pages={self.remaining_paid_pages}, "
            f"remaining_free_pages_today={self.remaining_free_pages_today}, "
            f"remaining_free_pages_this_month={self.remaining_free_pages_this_month}, "
            f"dashboard_url={self.dashboard_url!r})"
        )


def _handler_accepts_timeout(handler: Callable[..., Any]) -> bool:
    from inspect import Parameter, signature

    try:
        params = signature(handler).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(
        param.name == "timeout" or param.kind == Parameter.VAR_KEYWORD
        for param in params
    )


class Task:
    """Represents an async parsing task."""

    def __init__(
        self,
        task_id: str,
        refresh_handler: Optional[Callable[[str], dict]] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.id = task_id
        self.warnings: List[str] = list(warnings or [])
        self.completed = False
        self.status: Literal["queuing", "processing", "success", "failed"] = "queuing"
        self.record_id: Optional[int] = None
        self.file_name: Optional[str] = None
        self.pages: Optional[int] = None
        self._refresh_handler = refresh_handler
        self._result: Optional[ParseResponse] = None

    def refresh(self, timeout: Optional[float] = None) -> None:
        """Poll /parse/async_check for latest status."""
        if self._refresh_handler is None:
            raise RuntimeError("Task cannot refresh without a parser resource. Use client.parser.task(task_id).")
        if timeout is not None and _handler_accepts_timeout(self._refresh_handler):
            data = self._refresh_handler(self.id, timeout=timeout)
        else:
            data = self._refresh_handler(self.id)
        self._apply_api(data)

    def _apply_api(self, data: dict) -> None:
        self.warnings = collect_api_warnings(data)
        api_data = data.get("data") or {}
        raw_status = api_data.get("status", self.status)
        self.status = raw_status.lower()
        self.record_id = api_data.get("record_id")
        self.file_name = api_data.get("file_name")
        metadata = api_data.get("metadata") or {}
        self.pages = metadata.get("page_num")
        if self.status in ("success", "failed"):
            self.completed = True
            if self.status == "success":
                self._result = ParseResponse.from_api(data)

    def wait(self, poll_interval: float = 3.0, timeout: float = 120.0) -> ParseResponse:
        """Block until task completes or timeout."""
        import time
        from somark._exceptions import ParseTimeoutError, ParseFailedError
        deadline = time.monotonic() + timeout
        while not self.completed:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ParseTimeoutError(f"Task {self.id} timed out after {timeout}s")
            time.sleep(min(poll_interval, remaining))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ParseTimeoutError(f"Task {self.id} timed out after {timeout}s")
            try:
                self.refresh(timeout=remaining)
            except Exception as exc:
                if time.monotonic() >= deadline:
                    raise ParseTimeoutError(f"Task {self.id} timed out after {timeout}s") from exc
                raise
            if time.monotonic() >= deadline:
                raise ParseTimeoutError(f"Task {self.id} timed out after {timeout}s")
        if self.status == "failed":
            raise ParseFailedError(f"Task {self.id} failed")
        return self._result  # type: ignore

    def result(self) -> ParseResponse:
        if self._result is None:
            raise RuntimeError("Task not yet completed. Call wait() or refresh() first.")
        return self._result

    def __repr__(self) -> str:
        return f"Task(id={self.id!r}, status={self.status!r}, completed={self.completed})"


class AsyncTask:
    """Represents an async parsing task for AsyncSoMark."""

    def __init__(
        self,
        task_id: str,
        refresh_handler: Optional[Callable[[str], Awaitable[dict]]] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.id = task_id
        self.warnings: List[str] = list(warnings or [])
        self.completed = False
        self.status: Literal["queuing", "processing", "success", "failed"] = "queuing"
        self.record_id: Optional[int] = None
        self.file_name: Optional[str] = None
        self.pages: Optional[int] = None
        self._refresh_handler = refresh_handler
        self._result: Optional[ParseResponse] = None

    async def refresh(self) -> None:
        if self._refresh_handler is None:
            raise RuntimeError("Task cannot refresh without a parser resource. Use client.parser.task(task_id).")
        data = await self._refresh_handler(self.id)
        self._apply_api(data)

    def _apply_api(self, data: dict) -> None:
        self.warnings = collect_api_warnings(data)
        api_data = data.get("data") or {}
        raw_status = api_data.get("status", self.status)
        self.status = raw_status.lower()
        self.record_id = api_data.get("record_id")
        self.file_name = api_data.get("file_name")
        metadata = api_data.get("metadata") or {}
        self.pages = metadata.get("page_num")
        if self.status in ("success", "failed"):
            self.completed = True
            if self.status == "success":
                self._result = ParseResponse.from_api(data)

    async def wait(self, poll_interval: float = 3.0, timeout: float = 120.0) -> ParseResponse:
        import asyncio
        from somark._exceptions import ParseTimeoutError, ParseFailedError
        elapsed = 0.0
        while not self.completed:
            if elapsed >= timeout:
                raise ParseTimeoutError(f"Task {self.id} timed out after {timeout}s")
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
            await self.refresh()
        if self.status == "failed":
            raise ParseFailedError(f"Task {self.id} failed")
        return self._result  # type: ignore

    def result(self) -> ParseResponse:
        if self._result is None:
            raise RuntimeError("Task not yet completed.")
        return self._result


@dataclass
class ToImagesResult:
    ok: bool
    files: List[str] = field(default_factory=list)
    error: Optional[str] = None
