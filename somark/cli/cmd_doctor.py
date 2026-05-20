from __future__ import annotations
import typer
from pathlib import Path
from somark.cli._help import HELP_CONTEXT_SETTINGS, examples
from somark.cli._output import console, print_success, print_error, print_warning, print_info
from somark.resources.preview import _describe_vendor_source, _find_vendor_location, _validate_vendor_location

VIEWER_REPO_URL = "https://github.com/SoMarkAI/SoMarkDownViewer.git"


def _resolve_vendor_install_dir() -> Path:
    return Path.cwd() / "vendor" / "somarkdown-viewer"


def _placeholder_entries(target_dir: Path) -> list[str]:
    if not target_dir.is_dir():
        return []
    return [entry.name for entry in target_dir.iterdir() if entry.name != ".DS_Store"]


def _repair_viewer_install() -> None:
    import shutil
    import subprocess

    target_dir = _resolve_vendor_install_dir()
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    git_dir = target_dir / ".git"
    script = target_dir / "get_latest_smd.sh"

    if git_dir.exists():
        subprocess.run(["git", "-C", str(target_dir), "fetch", "--depth", "1", "origin", "main"], check=True)
        subprocess.run(["git", "-C", str(target_dir), "checkout", "main"], check=True)
        subprocess.run(["git", "-C", str(target_dir), "pull", "--ff-only", "origin", "main"], check=True)
    elif not target_dir.exists():
        subprocess.run(["git", "clone", "--depth", "1", VIEWER_REPO_URL, str(target_dir)], check=True)
    else:
        entries = _placeholder_entries(target_dir)
        is_placeholder = not entries or entries == [".gitkeep"]
        has_viewer_files = (target_dir / "index.html").exists() or script.exists()

        if is_placeholder:
            shutil.rmtree(target_dir)
            subprocess.run(["git", "clone", "--depth", "1", VIEWER_REPO_URL, str(target_dir)], check=True)
        elif not has_viewer_files:
            raise RuntimeError(
                f"Cannot repair preview assets automatically because {target_dir} exists but is not a SoMarkDownViewer checkout."
            )

    if script.exists():
        subprocess.run(["bash", str(script)], check=True)
        return

    raise RuntimeError(f"get_latest_smd.sh not found after repair in {target_dir}")

app = typer.Typer(
    help="Diagnose installation.",
    epilog=examples("somark doctor", "somark doctor fix", "somark doctor ping"),
    context_settings=HELP_CONTEXT_SETTINGS,
    invoke_without_command=True,
    no_args_is_help=False,
)


@app.callback(invoke_without_command=True, context_settings=HELP_CONTEXT_SETTINGS)
def doctor(ctx: typer.Context):
    if ctx.invoked_subcommand is None:
        _run_checks()


@app.command("fix", context_settings=HELP_CONTEXT_SETTINGS, epilog=examples("somark doctor fix"))
def fix():
    """Attempt to fix installation issues."""
    try:
        _repair_viewer_install()
        print_success("Preview assets repaired.")
    except Exception as e:
        print_error(f"Failed to repair preview assets: {e}")


@app.command("ping", context_settings=HELP_CONTEXT_SETTINGS, epilog=examples("somark doctor ping"))
def ping():
    """Check network connectivity."""
    import httpx
    targets = ["https://1.1.1.1", "https://somark.tech"]
    for target in targets:
        try:
            r = httpx.get(target, timeout=5)
            print_success(f"{target} ({r.status_code})")
        except Exception as e:
            print_error(f"{target}: {e}")


def _run_checks():
    console.print("[bold]SoMark Doctor[/bold]\n")
    # Python version
    import sys
    v = sys.version_info
    if v >= (3, 10):
        print_success(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        print_error(f"Python {v.major}.{v.minor} (>=3.10 required)")

    # sopdf
    try:
        import sopdf
        print_success("sopdf installed")
    except ImportError as exc:
        from somark.resources.pdf import pdf_dependency_error
        print_warning(pdf_dependency_error(exc))

    # API key
    from somark._config import resolve_config
    cfg = resolve_config()
    if cfg.get("api_key"):
        key = cfg["api_key"]
        masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "***"
        print_success(f"API key configured ({masked})")
    else:
        print_warning("API key not configured. Run: somark login")

    # preview assets
    vendor_location = _find_vendor_location()
    try:
        resolved_vendor_location = _validate_vendor_location(vendor_location)
        source = _describe_vendor_source(resolved_vendor_location.source)
        print_success(f"preview assets ready ({source}: {resolved_vendor_location.path})")
    except RuntimeError as exc:
        message = str(exc)
        if vendor_location and vendor_location.path.is_dir():
            print_warning(message)
        else:
            print_error(message)

    # network ping
    import httpx
    try:
        r = httpx.get("https://somark.tech", timeout=5)
        print_success(f"somark.tech reachable ({r.status_code})")
    except Exception as e:
        print_error(f"somark.tech unreachable: {e}")
