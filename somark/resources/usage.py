from __future__ import annotations
from somark._models import Usage
from somark._exceptions import AuthenticationError
from somark._warnings import emit_warnings


class UsageClient:
    def __init__(self, http):
        self._http = http

    def get(self) -> Usage:
        if not self._http.api_key:
            raise AuthenticationError("api_key is required for usage queries.")
        result = self._http.post("/usage", data={})
        usage = Usage.from_api(result)
        emit_warnings(usage.warnings)
        return usage


class AsyncUsageClient:
    def __init__(self, http):
        self._http = http

    async def get(self) -> Usage:
        if not self._http.api_key:
            raise AuthenticationError("api_key is required for usage queries.")
        result = await self._http.post("/usage", data={})
        usage = Usage.from_api(result)
        emit_warnings(usage.warnings)
        return usage
