from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, List, Optional

import typer
from rich.table import Table

from somark._models import OutputPlan, plan_output
from somark.cli._help import HELP_CONTEXT_SETTINGS, examples
from somark.cli._output import console, err_console, make_spinner, print_error, print_success
from somark.resources._parse_core import resolve_cli_file_inputs, run_limited_sync

PARSE_CONTEXT_SETTINGS = {**HELP_CONTEXT_SETTINGS, "allow_interspersed_args": True}

app = typer.Typer(
    help="Parse a document.",
    epilog=examples(
        "somark parse document.pdf --formats md,json --out parsed/",
        "somark parse a.pdf b.pdf --out parsed/",
        "somark parse --file-list files.txt --out parsed/",
        "somark parse document.pdf --async",
        "somark parse --task-id TASK_ID --wait",
    ),
    context_settings=PARSE_CONTEXT_SETTINGS,
    invoke_without_command=True,
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True, context_settings=PARSE_CONTEXT_SETTINGS)
def parse(
    ctx: typer.Context,
    files: Optional[List[str]] = typer.Argument(None, help="Path(s) to document file(s)"),
    formats: str = typer.Option("md", "--formats", help="Output formats (comma-separated): md,markdown,json,zip"),
    out: Optional[str] = typer.Option(None, "--out", help="Output file path"),
    file_list: Optional[str] = typer.Option(None, "--file-list", help="Text file with one document path per line"),
    image_fmt: str = typer.Option("url", "--image-fmt", help="Image return mode: url|base64|file|none"),
    formula_fmt: Optional[str] = typer.Option(None, "--formula-fmt", help="Formula format: latex|mathml|ascii"),
    table_fmt: Optional[str] = typer.Option(None, "--table-fmt", help="Table format: markdown|html|image"),
    cs_fmt: Optional[str] = typer.Option(None, "--cs-fmt", help="Chemical structure format: image"),
    title_levels: bool = typer.Option(False, "--title-levels", help="Enable title level recognition"),
    cross_page_text: bool = typer.Option(False, "--cross-page-text", help="Enable text cross-page merge"),
    cross_page_table: bool = typer.Option(False, "--cross-page-table", help="Enable table cross-page merge"),
    no_inline_image: bool = typer.Option(False, "--no-inline-image", help="Disable inline images"),
    no_table_image: bool = typer.Option(False, "--no-table-image", help="Disable table images"),
    no_image_understanding: bool = typer.Option(False, "--no-image-understanding", help="Disable image understanding"),
    keep_header_footer: bool = typer.Option(False, "--keep-header-footer", help="Keep headers and footers"),
    async_mode: bool = typer.Option(False, "--async", help="Submit async task only"),
    task_id: Optional[str] = typer.Option(None, "--task-id", help="Query/wait for existing task"),
    wait: bool = typer.Option(False, "--wait", help="Wait for async task (use with --task-id)"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
):
    from somark._exceptions import SoMarkError
    from somark._models import ElementFormats, ExtractConfig, normalize_save_formats
    from somark.cli.main import _make_client

    client = _make_client()
    fmt_list = normalize_save_formats(formats)
    extract_config = ExtractConfig(
        enable_title_level_recognition=title_levels,
        enable_text_cross_page=cross_page_text,
        enable_table_cross_page=cross_page_table,
        enable_inline_image=not no_inline_image,
        enable_table_image=not no_table_image,
        enable_image_understanding=not no_image_understanding,
        keep_header_footer=keep_header_footer,
    )
    element_formats = ElementFormats(image=image_fmt, formula=formula_fmt, table=table_fmt, cs=cs_fmt)
    input_files = _collect_input_files(files or [], file_list)
    is_batch = len(input_files) > 1 or file_list is not None

    try:
        if task_id:
            task = client.parser.task(task_id)
            if wait:
                stdout_mode = out is None and len(fmt_list) == 1
                if stdout_mode:
                    response = task.wait()
                else:
                    with make_spinner(f"Waiting for task {task_id}...") as progress:
                        progress.add_task("wait")
                        response = task.wait()
                response.source_file_name = response.source_file_name or task.file_name
                plan = plan_output(response.source_file_name or "output", out, fmt_list, allow_stdout=True)
                if plan.stdout:
                    console.print(response._content_for_format(fmt_list[0]), end="")
                    return
                _save_output_plan(response, plan)
                for output in _plan_paths(plan):
                    console.print(f"Output saved: {output}")
                print_success(f"Done in {response.pages} pages")
            else:
                task.refresh()
                console.print(f"Task {task_id}: status={task.status}")
            return

        if async_mode:
            if not input_files:
                print_error("File argument required for async mode")
                raise typer.Exit(3)
            if is_batch:
                with make_spinner("Submitting tasks...") as progress:
                    progress.add_task("submit")
                    tasks = client.parser.create(
                        file=input_files,
                        formats=fmt_list,
                        element_formats=element_formats,
                        extract_config=extract_config,
                    )
                _render_batch_results(input_files, list(tasks), async_mode=True, formats=fmt_list, out=out, verbose=verbose)
                return
            file = input_files[0]
            task = client.parser.create(
                file=file,
                formats=fmt_list,
                element_formats=element_formats,
                extract_config=extract_config,
            )
            console.print(f"Task submitted: {task.id}")
            console.print(f"Status: {task.status}")
            console.print("\nTo retrieve results later:")
            console.print(f"  somark parse --task-id {task.id} --wait")
            return

        if not input_files:
            print_error("File argument required")
            raise typer.Exit(3)
        if is_batch:
            _validate_batch_output(out, fmt_list)
            manifest = Path(out) / "somark-tasks.jsonl"
            manifest_lock = threading.Lock()

            def process_batch_file(file: str) -> dict:
                task_id = ""
                try:
                    task = client.parser.create(
                        file=file,
                        formats=fmt_list,
                        element_formats=element_formats,
                        extract_config=extract_config,
                    )
                    task_id = task.id
                    err_console.print(f"Task submitted: {file} -> {task_id}")
                    with manifest_lock:
                        with manifest.open("a", encoding="utf-8") as handle:
                            handle.write(json.dumps({"file": str(Path(file).resolve()), "task_id": task_id}) + "\n")
                            handle.flush()
                    response = task.wait(timeout=3600.0)
                    response.source_file_name = response.source_file_name or Path(file).name
                    plan = plan_output(file, out, fmt_list, batch=True)
                    _save_output_plan(response, plan)
                    return {"file": file, "task_id": task_id, "outputs": _plan_paths(plan), "error": ""}
                except Exception as exc:
                    return {"file": file, "task_id": task_id, "outputs": [], "error": str(exc)}

            with make_spinner("Submitting and processing files...") as progress:
                progress.add_task("parse")
                batch = run_limited_sync(input_files, process_batch_file)
            for warning in batch.warnings:
                console.print(f"Warning: {warning}")
            table = Table(title="Batch parse results")
            table.add_column("File")
            table.add_column("Status")
            table.add_column("Task ID")
            table.add_column("Output / Error")
            for item in batch.results:
                table.add_row(
                    item["file"],
                    "success" if not item["error"] else "failed",
                    item["task_id"],
                    ", ".join(item["outputs"]) if not item["error"] else item["error"],
                )
            console.print(table)
            console.print(f"Task manifest: {manifest}")
            failed = sum(bool(item["error"]) for item in batch.results)
            console.print(f"Summary: total={len(batch.results)} success={len(batch.results) - failed} failed={failed}")
            if failed:
                raise typer.Exit(1)
            return

        file = input_files[0]
        plan = plan_output(file, out, fmt_list, allow_stdout=True)
        if plan.stdout:
            task = client.parser.create(
                file=file,
                formats=fmt_list,
                element_formats=element_formats,
                extract_config=extract_config,
            )
            err_console.print(f"Task submitted: {task.id}; waiting for completion...")
            response = task.wait(timeout=3600.0)
            console.print(response._content_for_format(fmt_list[0]), end="")
            return

        with make_spinner(f"Submitting {file}...") as progress:
            progress.add_task("submit")
            task = client.parser.create(
                file=file,
                formats=fmt_list,
                element_formats=element_formats,
                extract_config=extract_config,
            )
        with make_spinner(f"Waiting for task {task.id}...") as progress:
            progress.add_task("wait")
            response = task.wait(timeout=3600.0)
        _save_output_plan(response, plan)
        print_success(f"Done in {response.pages} pages")
        for output in _plan_paths(plan):
            console.print(f"Output saved: {output}")
        if verbose:
            console.print(f"Task ID: {response.task_id}")
    except SoMarkError as e:
        print_error(str(e))
        raise typer.Exit(2 if "auth" in type(e).__name__.lower() or "connection" in type(e).__name__.lower() else 1)
    except ValueError as e:
        print_error(str(e))
        raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        raise typer.Exit(1)


def _collect_input_files(files: List[str], file_list: Optional[str]) -> List[str]:
    from somark._exceptions import InvalidParamError

    try:
        return resolve_cli_file_inputs(files, file_list).files
    except InvalidParamError as exc:
        print_error(str(exc))
        raise typer.Exit(3)


def _validate_batch_output(out: Optional[str], formats: List[str]) -> None:
    plan_output("output", out, formats, batch=True)


def _plan_paths(plan: OutputPlan) -> List[str]:
    return [target.path for target in plan.targets if target.path]


def _save_output_plan(response: Any, plan: OutputPlan) -> None:
    for target in plan.targets:
        if target.stdout or not target.path:
            continue
        response.save(target.path, format=target.format)


def _save_batch_outputs(files: List[str], responses: List[Any], out: Optional[str], formats: List[str]) -> None:
    for file, response in zip(files, responses):
        if not getattr(response, "source_file_name", None):
            response.source_file_name = Path(file).name
        _save_output_plan(response, plan_output(file, out, formats, batch=True))


def _render_batch_results(
    files: List[str],
    items: List[Any],
    *,
    async_mode: bool,
    formats: List[str],
    out: Optional[str],
    verbose: bool,
) -> None:
    console.print(f"Files: {len(files)}")
    table = Table(title="Parse Results", show_header=True, header_style="bold cyan")
    table.add_column("#", justify="right")
    table.add_column("File")
    table.add_column("Exists")
    table.add_column("Status")
    table.add_column("Output / Task")
    table.add_column("Error")
    for index, (file, item) in enumerate(zip(files, items), start=1):
        if async_mode:
            status = "submitted"
            output = getattr(item, "id", "")
        else:
            status = "success"
            output_plan = plan_output(file, out, formats, batch=True)
            output = ", ".join(_plan_paths(output_plan))
            task_id = getattr(item, "task_id", "")
            if verbose and task_id:
                output = f"{output} task={task_id}"
        table.add_row(str(index), file, "yes", status, str(output), "")
    console.print(table)
    console.print(f"Summary: total={len(items)} success={len(items)} failed=0")
