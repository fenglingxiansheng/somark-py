from __future__ import annotations

import warnings as _warnings
from typing import Any, Optional


class SoMarkWarning(Warning):
    """Warning category emitted by the SoMark SDK."""


def _dedupe(messages: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for message in messages:
        if message in seen:
            continue
        seen.add(message)
        result.append(message)
    return result


def collect_api_warnings(data: dict[str, Any]) -> list[str]:
    raw = data.get("warnings")
    if not isinstance(raw, list):
        return []
    messages = [item.strip() for item in raw if isinstance(item, str) and item.strip()]
    return _dedupe(messages)


def emit_warnings(messages: list[str]) -> None:
    for message in _dedupe(messages):
        _warnings.warn(message, SoMarkWarning, stacklevel=2)


def parse_max_concurrency(raw: Optional[str]) -> tuple[int, list[str]]:
    value = (raw or "").strip()
    if not value:
        return 1, []
    try:
        concurrency = int(value)
    except ValueError:
        return 1, [f'Invalid SOMARK_PARSE_MAX_CONCURRENCY="{value}"; using 1.']
    if concurrency < 1:
        return 1, [f'Invalid SOMARK_PARSE_MAX_CONCURRENCY="{value}"; using 1.']
    if concurrency >= 2:
        return concurrency, [
            f"SOMARK_PARSE_MAX_CONCURRENCY is set to {concurrency}. "
            "The official default quota is 1 for everyone; only users explicitly approved "
            "for higher concurrency should use 2 or above."
        ]
    return concurrency, []
