from __future__ import annotations
import typer
from somark.cli._help import HELP_CONTEXT_SETTINGS, examples
from somark.cli._output import console, print_success, print_error

app = typer.Typer(
    help="Manage configuration.",
    epilog=examples("somark config set api_key sk-...", "somark config get api_key", "somark config list"),
    context_settings=HELP_CONTEXT_SETTINGS,
    no_args_is_help=True,
)


@app.command("set", context_settings=HELP_CONTEXT_SETTINGS, epilog=examples("somark config set api_key sk-..."))
def config_set(
    key: str = typer.Argument(..., help="Config key (api_key, base_url, timeout, max_retries)"),
    value: str = typer.Argument(..., help="Config value"),
    show: bool = typer.Option(False, "--show", help="Show secret values in output"),
):
    from somark._config import save_config, mask_config_value
    try:
        save_config(**{key: value})
        display_value = value if show else mask_config_value(key, value)
        print_success(f"Set {key} = {display_value}")
    except Exception as e:
        print_error(str(e))
        raise typer.Exit(1)


@app.command("get", context_settings=HELP_CONTEXT_SETTINGS, epilog=examples("somark config get api_key"))
def config_get(
    key: str = typer.Argument(..., help="Config key"),
    show: bool = typer.Option(False, "--show", help="Show secret values in output"),
):
    from somark._config import get_config_value, mask_config_value
    val = get_config_value(key)
    if val is not None:
        display_value = val if show else mask_config_value(key, str(val))
        console.print(f"{key} = {display_value}")
    else:
        console.print(f"{key} is not set")


@app.command("list", context_settings=HELP_CONTEXT_SETTINGS, epilog=examples("somark config list"))
def config_list(
    show: bool = typer.Option(False, "--show", help="Show secret values in output"),
):
    """List all config values (effective: env > file > default)."""
    from somark._config import list_resolved_config, mask_config_value

    def _source_label(source: str) -> str:
        colors = {"env": "cyan", "file": "yellow", "default": "dim"}
        return f"[{colors.get(source, '')}][{source}][/{colors.get(source, '')}]"

    entries = list_resolved_config()
    for entry in entries:
        value = str(entry["value"])
        display_value = value if show else mask_config_value(entry["key"], value)
        console.print(f"{entry['key']} = {display_value}  {_source_label(entry['source'])}")
