from __future__ import annotations
import typer
from typing import Optional
from somark.cli._help import HELP_CONTEXT_SETTINGS, examples
from somark.cli._output import print_error, print_success, console

app = typer.Typer(
    help="PDF operations.",
    epilog=examples("somark pdf toimg document.pdf --out ./pages"),
    context_settings=HELP_CONTEXT_SETTINGS,
    no_args_is_help=True,
)


@app.command(
    "toimg",
    context_settings=HELP_CONTEXT_SETTINGS,
    epilog=examples("somark pdf toimg document.pdf --out ./pages"),
)
def toimg(
    file: str = typer.Argument(..., help="PDF file path"),
    out: str = typer.Option("./", "--out", help="Output directory"),
    format: Optional[str] = typer.Option(None, "--format", help="Filename template: {name}.page-{n}.png"),
    dpi: int = typer.Option(150, "--dpi", help="Resolution in DPI"),
):
    from somark.resources.pdf import PDFProcessor
    pdf = PDFProcessor()
    result = pdf.to_images(file=file, out=out, filename_format=format, dpi=dpi)
    if result.ok:
        print_success(f"Converted {len(result.files)} page(s) to {out}")
        for f in result.files:
            console.print(f"  {f}")
    else:
        print_error(result.error or "Unknown error")
        raise typer.Exit(1)
