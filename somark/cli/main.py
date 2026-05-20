from __future__ import annotations
import typer
from typing import Optional
from somark.cli._help import HELP_CONTEXT_SETTINGS, examples
from somark._warnings import SoMarkWarning

app = typer.Typer(
    name="somark",
    help="SoMark SDK + CLI — Document parsing, PDF processing, and SoMarkDown preview. [PY]",
    epilog=examples("somark parse document.pdf --formats md,json --out output.md", "somark usage --format table"),
    context_settings=HELP_CONTEXT_SETTINGS,
    add_completion=False,
    invoke_without_command=True,
)

# Global options stored for subcommands
_api_key: Optional[str] = None
_base_url: Optional[str] = None
_timeout: Optional[float] = None


@app.callback(invoke_without_command=True, context_settings=HELP_CONTEXT_SETTINGS)
def main(
    ctx: typer.Context,
    api_key: Optional[str] = typer.Option(None, "--api-key", envvar="SOMARK_API_KEY", help="API key"),
    base_url: Optional[str] = typer.Option(None, "--base-url", help="Base URL"),
    timeout: Optional[float] = typer.Option(None, "--timeout", help="Request timeout (seconds)"),
    no_warnings: bool = typer.Option(False, "--no-warnings", help="Suppress SoMark warnings"),
    version: bool = typer.Option(False, "--version", "-v", help="Show version and exit", is_eager=True),
):
    import warnings

    global _api_key, _base_url, _timeout
    _api_key = api_key
    _base_url = base_url
    _timeout = timeout
    warnings.simplefilter("ignore" if no_warnings else "default", SoMarkWarning)
    if version:
        from somark import __version__
        typer.echo(f"somark {__version__}")
        raise typer.Exit()
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def _make_client():
    from somark import SoMark
    return SoMark(api_key=_api_key, base_url=_base_url, timeout=_timeout)


# Import and add subcommands
from somark.cli import cmd_parse, cmd_usage, cmd_pdf, cmd_preview, cmd_doctor, cmd_config, cmd_login

app.add_typer(cmd_parse.app, name="parse")
app.command("usage", context_settings=HELP_CONTEXT_SETTINGS, epilog=examples("somark usage --format table"))(cmd_usage.usage)
app.add_typer(cmd_pdf.app, name="pdf")
app.command("preview", context_settings=HELP_CONTEXT_SETTINGS, epilog=examples("somark preview output.md --port 7878"))(cmd_preview.preview)
app.add_typer(cmd_doctor.app, name="doctor")
app.add_typer(cmd_config.app, name="config")
app.command("login", context_settings=HELP_CONTEXT_SETTINGS, epilog=examples("somark login --no-open"))(cmd_login.login)
