from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Dict, Union, overload

from somark._models import ParseResponse, Task, AsyncTask, ExtractConfig, ElementFormats
from somark._exceptions import AuthenticationError
from somark._warnings import collect_api_warnings, emit_warnings
from somark.resources._parse_core import (
    FileInput,
    attach_warnings,
    build_parse_data,
    ensure_files_exist,
    resolve_file_inputs,
    run_limited_async,
    run_limited_sync,
)


class DocumentParser:
    def __init__(self, http):
        self._http = http

    def _check_api_key(self):
        if not self._http.api_key:
            raise AuthenticationError("api_key is required for parser operations.")

    def _poll_task(self, task_id: str, timeout: Optional[float] = None) -> dict:
        self._check_api_key()
        kwargs = {"timeout": timeout} if timeout is not None else {}
        data = self._http.post("/parse/async_check", data={"task_id": task_id}, **kwargs)
        emit_warnings(collect_api_warnings(data))
        return data

    def task(self, task_id: str) -> Task:
        return Task(task_id, self._poll_task)

    def _parse_one(
        self,
        file: str,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
    ) -> ParseResponse:
        self._check_api_key()
        data = build_parse_data(formats or ["md"], element_formats, extract_config)
        with open(file, "rb") as f:
            files = {"file": (file, f, "application/octet-stream")}
            result = self._http.post("/parse/sync", data=data, files=files)
        response = ParseResponse.from_api(result)
        emit_warnings(response.warnings)
        response.source_file_name = Path(file).name
        return response

    @overload
    def parse(
        self,
        file: str,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> ParseResponse: ...

    @overload
    def parse(
        self,
        file: List[str],
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> List[ParseResponse]: ...

    def parse(
        self,
        file: FileInput,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> Union[ParseResponse, List[ParseResponse]]:
        self._check_api_key()
        resolved = resolve_file_inputs(file, file_list=file_list)
        ensure_files_exist(resolved.files)
        batch = run_limited_sync(
            resolved.files,
            lambda item: self._parse_one(
                item, formats=formats, element_formats=element_formats, extract_config=extract_config
            ),
        )
        if resolved.is_batch:
            emit_warnings(batch.warnings)
        attach_warnings(batch.results, batch.warnings if resolved.is_batch else [])
        return batch.results if resolved.is_batch else batch.results[0]

    def _create_one(
        self,
        file: str,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
    ) -> Task:
        self._check_api_key()
        data = build_parse_data(formats or ["md"], element_formats, extract_config)
        with open(file, "rb") as f:
            files = {"file": (file, f, "application/octet-stream")}
            result = self._http.post("/parse/async", data=data, files=files)
        task_id = result.get("data", {}).get("task_id", "")
        warnings = collect_api_warnings(result)
        emit_warnings(warnings)
        return Task(task_id, self._poll_task, warnings=warnings)

    @overload
    def create(
        self,
        file: str,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> Task: ...

    @overload
    def create(
        self,
        file: List[str],
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> List[Task]: ...

    def create(
        self,
        file: FileInput,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> Union[Task, List[Task]]:
        self._check_api_key()
        resolved = resolve_file_inputs(file, file_list=file_list)
        ensure_files_exist(resolved.files)
        batch = run_limited_sync(
            resolved.files,
            lambda item: self._create_one(
                item, formats=formats, element_formats=element_formats, extract_config=extract_config
            ),
        )
        if resolved.is_batch:
            emit_warnings(batch.warnings)
        attach_warnings(batch.results, batch.warnings if resolved.is_batch else [])
        return batch.results if resolved.is_batch else batch.results[0]


class AsyncDocumentParser:
    def __init__(self, http):
        self._http = http

    def _check_api_key(self):
        if not self._http.api_key:
            raise AuthenticationError("api_key is required for parser operations.")

    async def _poll_task(self, task_id: str) -> dict:
        self._check_api_key()
        data = await self._http.post("/parse/async_check", data={"task_id": task_id})
        emit_warnings(collect_api_warnings(data))
        return data

    def task(self, task_id: str) -> AsyncTask:
        return AsyncTask(task_id, self._poll_task)

    async def _parse_one(
        self,
        file: str,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
    ) -> ParseResponse:
        self._check_api_key()
        data = build_parse_data(formats or ["md"], element_formats, extract_config)
        with open(file, "rb") as f:
            files = {"file": (file, f, "application/octet-stream")}
            result = await self._http.post("/parse/sync", data=data, files=files)
        response = ParseResponse.from_api(result)
        emit_warnings(response.warnings)
        response.source_file_name = Path(file).name
        return response

    @overload
    async def parse(
        self,
        file: str,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> ParseResponse: ...

    @overload
    async def parse(
        self,
        file: List[str],
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> List[ParseResponse]: ...

    async def parse(
        self,
        file: FileInput,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> Union[ParseResponse, List[ParseResponse]]:
        self._check_api_key()
        resolved = resolve_file_inputs(file, file_list=file_list)
        ensure_files_exist(resolved.files)
        batch = await run_limited_async(
            resolved.files,
            lambda item: self._parse_one(
                item, formats=formats, element_formats=element_formats, extract_config=extract_config
            ),
        )
        if resolved.is_batch:
            emit_warnings(batch.warnings)
        attach_warnings(batch.results, batch.warnings if resolved.is_batch else [])
        return batch.results if resolved.is_batch else batch.results[0]

    async def _create_one(
        self,
        file: str,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
    ) -> AsyncTask:
        self._check_api_key()
        data = build_parse_data(formats or ["md"], element_formats, extract_config)
        with open(file, "rb") as f:
            files = {"file": (file, f, "application/octet-stream")}
            result = await self._http.post("/parse/async", data=data, files=files)
        task_id = result.get("data", {}).get("task_id", "")
        warnings = collect_api_warnings(result)
        emit_warnings(warnings)
        return AsyncTask(task_id, self._poll_task, warnings=warnings)

    @overload
    async def create(
        self,
        file: str,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> AsyncTask: ...

    @overload
    async def create(
        self,
        file: List[str],
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> List[AsyncTask]: ...

    async def create(
        self,
        file: FileInput,
        formats: Optional[List[str]] = None,
        element_formats: Optional[Union[ElementFormats, Dict]] = None,
        extract_config: Optional[Union[ExtractConfig, Dict]] = None,
        file_list: bool = False,
    ) -> Union[AsyncTask, List[AsyncTask]]:
        self._check_api_key()
        resolved = resolve_file_inputs(file, file_list=file_list)
        ensure_files_exist(resolved.files)
        batch = await run_limited_async(
            resolved.files,
            lambda item: self._create_one(
                item, formats=formats, element_formats=element_formats, extract_config=extract_config
            ),
        )
        if resolved.is_batch:
            emit_warnings(batch.warnings)
        attach_warnings(batch.results, batch.warnings if resolved.is_batch else [])
        return batch.results if resolved.is_batch else batch.results[0]
