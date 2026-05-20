from __future__ import annotations
from typing import Any, Iterable
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from somark._warnings import emit_warnings

console = Console()
err_console = Console(stderr=True)


def print_success(msg: str) -> None:
    console.print(f"[green]✓[/green] {msg}")


def print_error(msg: str) -> None:
    err_console.print(f"[red]✗[/red] {msg}")


def print_info(msg: str) -> None:
    console.print(f"[blue]ℹ[/blue] {msg}")


def print_warning(msg: str) -> None:
    emit_warnings([msg])


def print_warnings(warnings: Iterable[Any]) -> None:
    emit_warnings([str(warning) for warning in warnings if warning])


def make_spinner(description: str = "Working...") -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        transient=True,
    )


def print_usage_table(
    remaining_paid_pages: int,
    remaining_free_pages_today: int,
    remaining_free_pages_this_month: int,
    dashboard_url: str,
) -> None:
    table = Table(title="SoMark Usage", show_header=True, header_style="bold cyan")
    table.add_column("Field", style="dim")
    table.add_column("Value")
    table.add_row("Paid Pages Remaining", f"{remaining_paid_pages:,}")
    table.add_row("Free Pages Today", f"{remaining_free_pages_today:,}")
    table.add_row("Free Pages This Month", f"{remaining_free_pages_this_month:,}")
    table.add_row("Dashboard", dashboard_url)
    console.print(table)


def print_parse_result(response: Any, out_path: Optional[str] = None) -> None:
    console.print(f"[green]✓[/green] Done")
    if out_path:
        console.print(f"Output saved: {out_path}")
    console.print(f"Pages: {response.pages}  |  Task ID: {response.task_id}")
