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
        timeout: Optional[float] = None,
    ) -> dict:
        url = self.base_url + path
        form_data = self._build_data(data or {})
        # Parse submission timeouts are ambiguous: the server may have created a task.
        # Disable retries for both submission endpoints; status queries remain retryable.
        retry_safe = not (path in ("/parse/sync", "/parse/async") and files)
        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                if files:
                    response = self._client.post(url, data=form_data, files=files, **({"timeout": timeout} if timeout is not None else {}))
                else:
                    response = self._client.post(url, data=form_data, **({"timeout": timeout} if timeout is not None else {}))
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
                # Skipping the delay alone would still continue the loop and resend the request.
                if not retry_safe or attempt >= self.max_retries:
                    raise last_exc
                time.sleep(2 ** attempt)
            except httpx.TimeoutException as e:
                message = str(e)
                if not retry_safe:
                    if path == "/parse/async":
                        message = "Connection timed out."
                    else:
                        message = "Connection timed out. Please use the async API."
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
        # Both endpoints create parse tasks; do not resend after an ambiguous timeout.
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
                # Raise immediately so the loop cannot submit the file again.
                if not retry_safe or attempt >= self.max_retries:
                    raise last_exc
                await asyncio.sleep(2 ** attempt)
            except httpx.TimeoutException as e:
                message = str(e)
                if not retry_safe:
                    if path == "/parse/async":
                        message = "Connection timed out."
                    else:
                        message = "Connection timed out. Please use the async API."
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
