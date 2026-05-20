from __future__ import annotations
import json
import typer
from typing import Optional
from somark.cli._output import print_error, print_usage_table


def usage(
    format: str = typer.Option("table", "--format", help="Output format: text|json|table"),
):
    from somark.cli.main import _make_client
    from somark._exceptions import SoMarkError
    client = _make_client()
    try:
        u = client.usage.get()
        if format == "json":
            typer.echo(json.dumps(u.model_dump(), indent=2))
        elif format == "text":
            typer.echo(f"Paid Pages Remaining:  {u.remaining_paid_pages:,}")
            typer.echo(f"Free Pages Today:      {u.remaining_free_pages_today:,}")
            typer.echo(f"Free Pages This Month: {u.remaining_free_pages_this_month:,}")
            typer.echo(f"Dashboard: {u.dashboard_url}")
        else:
            print_usage_table(
                u.remaining_paid_pages,
                u.remaining_free_pages_today,
                u.remaining_free_pages_this_month,
                u.dashboard_url,
            )
    except SoMarkError as e:
        print_error(str(e))
        raise typer.Exit(2)
