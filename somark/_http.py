from __future__ import annotations
import time
from typing import Optional, Any, Dict

import httpx

from somark._exceptions import (
    raise_for_code,
    AuthenticationError,
    ConnectionError,
    TimeoutError,
    RateLimitError,
    APIError,
)

# Codes that trigger automatic retry
RETRY_CODES = {1101, 1124}
RETRY_HTTP_STATUSES = {500, 502, 503, 504}


class HttpClient:
    def __init__(
        self,
        api_key: Optional[str],
        base_url: str,
        timeout: float,
        max_retries: int,
        http_client: Optional[httpx.Client] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = http_client or httpx.Client(timeout=timeout)
        self._own_client = http_client is None

    def _build_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(data)
        if self.api_key:
            result["api_key"] = self.api_key
        return result

    def post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> dict:
        url = self.base_url + path
        form_data = self._build_data(data or {})
        # 解析上传超时结果不确定：服务端可能已创建任务，因此禁止自动重提。
        # 同时覆盖 sync/async 两个提交端点；状态查询等其他请求仍可按 max_retries 重试。
        retry_safe = not (path in ("/parse/sync", "/parse/async") and files)
        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                if files:
                    response = self._client.post(url, data=form_data, files=files)
                else:
                    response = self._client.post(url, data=form_data)
                if response.status_code in RETRY_HTTP_STATUSES and retry_safe and attempt < self.max_retries:
                    time.sleep(2 ** attempt)
                    continue
                response.raise_for_status()
                result = response.json()
                code = result.get("code", -1)
                if code != 0:
                    if code in RETRY_CODES and retry_safe and attempt < self.max_retries:
                        time.sleep(2 ** attempt)
                        continue
                    raise_for_code(code, result.get("message", result.get("msg", "")))
                return result
            except httpx.ConnectError as e:
                last_exc = ConnectionError(str(e))
                # 不能只跳过退避等待，否则循环仍会再次发送请求；不安全请求必须立即退出。
                if not retry_safe or attempt >= self.max_retries:
                    raise last_exc
                time.sleep(2 ** attempt)
            except httpx.TimeoutException as e:
                message = str(e)
                if not retry_safe:
                    # 客户端超时不代表服务端任务取消，提示用户先确认状态或改用异步提交。
                    message += ". The server may have accepted this parse request. Do not resubmit; this request did not return a task ID, so contact support to check its status."
                last_exc = TimeoutError(message)
                if not retry_safe or attempt >= self.max_retries:
                    raise last_exc
                time.sleep(2 ** attempt)
            except (AuthenticationError, APIError):
                raise
        raise last_exc or APIError("Request failed after retries")

    def close(self) -> None:
        if self._own_client:
            self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class AsyncHttpClient:
    def __init__(
        self,
        api_key: Optional[str],
        base_url: str,
        timeout: float,
        max_retries: int,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self._client = http_client or httpx.AsyncClient(timeout=timeout)
        self._own_client = http_client is None

    def _build_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        result = dict(data)
        if self.api_key:
            result["api_key"] = self.api_key
        return result

    async def post(
        self,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        files: Optional[Dict[str, Any]] = None,
    ) -> dict:
        import asyncio
        url = self.base_url + path
        form_data = self._build_data(data or {})
        # sync/async 都会创建解析任务；超时后不重发，避免后台已接收时重复派发。
        retry_safe = not (path in ("/parse/sync", "/parse/async") and files)
        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                if files:
                    response = await self._client.post(url, data=form_data, files=files)
                else:
                    response = await self._client.post(url, data=form_data)
                if response.status_code in RETRY_HTTP_STATUSES and retry_safe and attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)
                    continue
                response.raise_for_status()
                result = response.json()
                code = result.get("code", -1)
                if code != 0:
                    if code in RETRY_CODES and retry_safe and attempt < self.max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise_for_code(code, result.get("message", result.get("msg", "")))
                return result
            except httpx.ConnectError as e:
                last_exc = ConnectionError(str(e))
                # 不安全请求直接抛出，不能让 for 循环进入下一次上传。
                if not retry_safe or attempt >= self.max_retries:
                    raise last_exc
                await asyncio.sleep(2 ** attempt)
            except httpx.TimeoutException as e:
                message = str(e)
                if not retry_safe:
                    # 同步解析请求超时时提醒：后台任务可能仍在运行，不要盲目重新提交。
                    message += ". The server may have accepted this parse request. Do not resubmit; this request did not return a task ID, so contact support to check its status."
                last_exc = TimeoutError(message)
                if not retry_safe or attempt >= self.max_retries:
                    raise last_exc
                await asyncio.sleep(2 ** attempt)
            except Exception:
                raise
        raise last_exc or APIError("Request failed after retries")

    async def close(self) -> None:
        if self._own_client:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
