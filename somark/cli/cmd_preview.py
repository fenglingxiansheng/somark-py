from __future__ import annotations
import typer
from typing import Optional
from somark.cli._output import print_error, print_info, console


def preview(
    file: Optional[str] = typer.Argument(None, help="File to preview (.md or .smd)"),
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind"),
    port: int = typer.Option(7878, "--port", help="Port to listen on"),
    no_open: bool = typer.Option(False, "--no-open", help="Don't open browser"),
):
    from somark.resources.preview import SoMarkDownPreview
    preview_res = SoMarkDownPreview()
    try:
        server = preview_res.start(file=file, host=host, port=port, open_browser=not no_open)
        console.print(f"[green]Preview server started:[/green] {server.url}")
        if file:
            console.print(f"File URL: {server.file_url}")
        console.print("Press Ctrl+C to stop.")
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            server.stop()
            console.print("\n[yellow]Server stopped.[/yellow]")
    except RuntimeError as e:
        print_error(str(e))
        raise typer.Exit(1)
