from __future__ import annotations
import typer
from somark.cli._output import console, print_success, print_error


def login(
    no_open: bool = typer.Option(False, "--no-open", help="Don't open browser"),
):
    """Login to SoMark and save API key."""
    url = "https://somark.tech/workbench/apikey"
    if not no_open:
        import webbrowser
        console.print(f"Opening {url} in your browser...")
        webbrowser.open(url)
    else:
        console.print(f"Visit {url} to get your API key.")

    api_key = typer.prompt("Enter your API key", hide_input=True)
    if not api_key.startswith("sk-"):
        print_error("Invalid API key format (should start with 'sk-')")
        raise typer.Exit(1)

    from somark._config import save_config
    save_config(api_key=api_key)
    print_success("Authenticated. Config saved to ~/.somark/config.toml")
