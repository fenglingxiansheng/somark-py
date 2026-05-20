from __future__ import annotations

HELP_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


def examples(*commands: str) -> str:
    return "Examples:\n\n" + "\n\n".join(f"  {command}" for command in commands)
