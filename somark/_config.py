from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Callable, Optional

DEFAULT_BASE_URL = "https://somark.tech/api/v1"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 2
CONFIG_FILE = Path.home() / ".somark" / "config.toml"


ConfigParser = Callable[[Any], Any]
ConfigValidator = Callable[[str, Any], None]
ConfigMasker = Callable[[str], str]
ConfigFormatter = Callable[[Any], str]


@dataclass(frozen=True)
class ConfigEntry:
    key: str
    env_var: str
    option_key: str
    default: Any
    parser: ConfigParser
    validator: ConfigValidator
    masker: ConfigMasker
    formatter: ConfigFormatter
    show_when_unset: bool


def _parse_optional_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def _parse_str(value: Any) -> str:
    return str(value)


def _parse_float(value: Any) -> float:
    return float(value)


def _parse_int(value: Any) -> int:
    return int(value)


def _validate_any(_key: str, _value: Any) -> None:
    return None


def _validate_base_url(key: str, value: Any) -> None:
    if value is not None and not str(value).startswith(("http://", "https://")):
        raise ValueError(f'Invalid {key} "{value}". Must start with http:// or https://')


def _mask_identity(value: str) -> str:
    return value


def _mask_api_key(value: str) -> str:
    return f"{value[:4]}...{value[-4:]}" if len(value) > 8 else "***"


def _format_default(value: Any) -> str:
    return str(value)


def _format_float(value: Any) -> str:
    numeric = float(value)
    return str(int(numeric)) if numeric.is_integer() else str(numeric)


CONFIG_SCHEMA: tuple[ConfigEntry, ...] = (
    ConfigEntry(
        key="api_key",
        env_var="SOMARK_API_KEY",
        option_key="api_key",
        default=None,
        parser=_parse_optional_str,
        validator=_validate_any,
        masker=_mask_api_key,
        formatter=_format_default,
        show_when_unset=False,
    ),
    ConfigEntry(
        key="base_url",
        env_var="SOMARK_BASE_URL",
        option_key="base_url",
        default=DEFAULT_BASE_URL,
        parser=_parse_str,
        validator=_validate_base_url,
        masker=_mask_identity,
        formatter=_format_default,
        show_when_unset=True,
    ),
    ConfigEntry(
        key="timeout",
        env_var="SOMARK_TIMEOUT",
        option_key="timeout",
        default=DEFAULT_TIMEOUT,
        parser=_parse_float,
        validator=_validate_any,
        masker=_mask_identity,
        formatter=_format_float,
        show_when_unset=True,
    ),
    ConfigEntry(
        key="max_retries",
        env_var="SOMARK_MAX_RETRIES",
        option_key="max_retries",
        default=DEFAULT_MAX_RETRIES,
        parser=_parse_int,
        validator=_validate_any,
        masker=_mask_identity,
        formatter=_format_default,
        show_when_unset=True,
    ),
)

CONFIG_SCHEMA_BY_KEY = {entry.key: entry for entry in CONFIG_SCHEMA}
VALID_CONFIG_KEYS = set(CONFIG_SCHEMA_BY_KEY)


def _load_toml_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        import toml
        return toml.load(CONFIG_FILE)
    except Exception:
        return {}


def _resolve_entry(
    entry: ConfigEntry,
    *,
    explicit_options: dict[str, Any],
    file_cfg: dict,
) -> tuple[Any, str]:
    if entry.option_key in explicit_options and explicit_options[entry.option_key] is not None:
        raw_value = explicit_options[entry.option_key]
        source = "explicit"
    elif os.environ.get(entry.env_var):
        raw_value = os.environ[entry.env_var]
        source = "env"
    elif file_cfg.get(entry.key) is not None:
        raw_value = file_cfg[entry.key]
        source = "file"
    else:
        raw_value = entry.default
        source = "default"

    value = entry.parser(raw_value)
    entry.validator(entry.key, value)
    return value, source


def resolve_config(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    timeout: Optional[float] = None,
    max_retries: Optional[int] = None,
) -> dict:
    """Resolve configuration from param > env > file, with fallback defaults."""
    file_cfg = _load_toml_config()
    explicit_options = {
        "api_key": api_key,
        "base_url": base_url,
        "timeout": timeout,
        "max_retries": max_retries,
    }
    return {
        entry.key: _resolve_entry(entry, explicit_options=explicit_options, file_cfg=file_cfg)[0]
        for entry in CONFIG_SCHEMA
    }


def save_config(**kwargs) -> None:
    """Write key-value pairs to ~/.somark/config.toml."""
    import toml
    for key, value in kwargs.items():
        entry = CONFIG_SCHEMA_BY_KEY.get(key)
        if entry is None:
            raise ValueError(f'Unknown config key "{key}". Valid keys: {", ".join(sorted(VALID_CONFIG_KEYS))}')
        if value is not None:
            parsed_value = entry.parser(value)
            entry.validator(key, parsed_value)
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    cfg = _load_toml_config()
    cfg.update({k: v for k, v in kwargs.items() if v is not None})
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        toml.dump(cfg, f)
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass


def get_config_value(key: str) -> Optional[str]:
    cfg = _load_toml_config()
    return cfg.get(key)


def mask_config_value(key: str, value: str) -> str:
    entry = CONFIG_SCHEMA_BY_KEY.get(key)
    if entry is None:
        return value
    return entry.masker(value)


def list_config() -> dict:
    return _load_toml_config()


def list_resolved_config() -> list[dict]:
    """Return all config keys with their effective values and sources."""
    file_cfg = _load_toml_config()
    entries = []

    for entry in CONFIG_SCHEMA:
        value, source = _resolve_entry(entry, explicit_options={}, file_cfg=file_cfg)
        if value is None and not entry.show_when_unset:
            continue
        entries.append({"key": entry.key, "value": entry.formatter(value), "source": source})

    return entries
