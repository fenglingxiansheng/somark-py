from __future__ import annotations
from typing import Optional
import httpx

from somark._config import resolve_config
from somark._http import HttpClient, AsyncHttpClient
from somark._exceptions import AuthenticationError
from somark.resources.parser import DocumentParser, AsyncDocumentParser
from somark.resources.usage import UsageClient, AsyncUsageClient
from somark.resources.pdf import PDFProcessor
from somark.resources.preview import SoMarkDownPreview


class SoMark:
    """Synchronous SoMark client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        http_client: Optional[httpx.Client] = None,
    ):
        cfg = resolve_config(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries)
        self._http = HttpClient(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
            timeout=cfg["timeout"],
            max_retries=cfg["max_retries"],
            http_client=http_client,
        )
        self.parser = DocumentParser(self._http)
        self.usage = UsageClient(self._http)
        self.pdf = PDFProcessor()
        self.preview = SoMarkDownPreview()

    def _require_api_key(self) -> None:
        if not self._http.api_key:
            raise AuthenticationError("api_key is required. Set it via SoMark(api_key=...) or SOMARK_API_KEY env var.")

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self) -> str:
        key = self._http.api_key
        masked = f"{key[:4]}...{key[-4:]}" if key and len(key) > 8 else ("set" if key else "not set")
        return f"SoMark(api_key={masked!r}, base_url={self._http.base_url!r})"


class AsyncSoMark:
    """Asynchronous SoMark client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        cfg = resolve_config(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=max_retries)
        self._http = AsyncHttpClient(
            api_key=cfg["api_key"],
            base_url=cfg["base_url"],
            timeout=cfg["timeout"],
            max_retries=cfg["max_retries"],
            http_client=http_client,
        )
        self.parser = AsyncDocumentParser(self._http)
        self.usage = AsyncUsageClient(self._http)
        self.pdf = PDFProcessor()
        self.preview = SoMarkDownPreview()

    async def close(self) -> None:
        await self._http.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
