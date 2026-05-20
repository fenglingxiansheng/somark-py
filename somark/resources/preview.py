from __future__ import annotations

import mimetypes
import threading
import time
import urllib.parse
import webbrowser
from dataclasses import dataclass
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Literal, Optional

SUPPORTED_PREVIEW_EXTS = {".md", ".smd"}
VENDOR_FIX_HINT = "Run: git submodule update --init --recursive or somark doctor fix"
_VENDOR_RELATIVE_PATH = Path("vendor") / "somarkdown-viewer"
VendorSource = Literal["package", "development"]


@dataclass(frozen=True)
class _VendorLocation:
    path: Path
    source: VendorSource


def _package_vendor_dir() -> Optional[Path]:
    try:
        import somark

        return Path(somark.__file__).resolve().parent / _VENDOR_RELATIVE_PATH
    except Exception:
        return None


def _development_vendor_dir() -> Path:
    return Path.cwd() / _VENDOR_RELATIVE_PATH


def _candidate_vendor_locations() -> list[_VendorLocation]:
    raw_candidates: list[_VendorLocation] = []
    package_vendor_dir = _package_vendor_dir()
    if package_vendor_dir is not None:
        raw_candidates.append(_VendorLocation(package_vendor_dir, "package"))
    raw_candidates.append(_VendorLocation(_development_vendor_dir(), "development"))

    candidates: list[_VendorLocation] = []
    seen: set[Path] = set()
    for candidate in raw_candidates:
        resolved = candidate.path.resolve()
        if resolved not in seen:
            seen.add(resolved)
            candidates.append(_VendorLocation(resolved, candidate.source))
    return candidates


def _describe_vendor_source(source: VendorSource) -> str:
    if source == "package":
        return "package assets"
    return "development checkout"


def _find_vendor_location() -> Optional[_VendorLocation]:
    for candidate in _candidate_vendor_locations():
        if candidate.path.is_dir():
            return candidate
    return None


def _find_vendor_dir() -> Optional[Path]:
    location = _find_vendor_location()
    return location.path if location is not None else None


def _missing_vendor_entries(vendor_dir: Path) -> list[str]:
    missing = []
    for required in (vendor_dir / "index.html", vendor_dir / "lib"):
        if not required.exists():
            missing.append(required.name)
    return missing


def _validate_vendor_dir(vendor_dir: Optional[Path]) -> Path:
    if vendor_dir is None:
        raise RuntimeError(f"vendor/somarkdown-viewer not found. {VENDOR_FIX_HINT}")

    missing = _missing_vendor_entries(vendor_dir)
    if missing:
        missing_text = ", ".join(missing)
        raise RuntimeError(f"vendor/somarkdown-viewer is incomplete. Missing {missing_text}. {VENDOR_FIX_HINT}")

    return vendor_dir


def _validate_vendor_location(vendor_location: Optional[_VendorLocation]) -> _VendorLocation:
    if vendor_location is None:
        raise RuntimeError(f"vendor/somarkdown-viewer not found. {VENDOR_FIX_HINT}")

    missing = _missing_vendor_entries(vendor_location.path)
    if missing:
        missing_text = ", ".join(missing)
        if vendor_location.source == "package":
            raise RuntimeError(
                f"Installed preview assets are incomplete. Missing {missing_text}. "
                "Reinstall the package or rebuild it with bundled viewer assets."
            )
        raise RuntimeError(f"vendor/somarkdown-viewer is incomplete. Missing {missing_text}. {VENDOR_FIX_HINT}")

    return vendor_location


class _PreviewFile:
    def __init__(self, file_path: str):
        absolute_path = Path(file_path).expanduser().resolve()
        if not absolute_path.is_file():
            raise RuntimeError(f"Preview file not found: {absolute_path}")
        if absolute_path.suffix.lower() not in SUPPORTED_PREVIEW_EXTS:
            suffix = absolute_path.suffix or "(no extension)"
            raise RuntimeError(f"Unsupported preview file type: {suffix}. Use .md or .smd.")

        self.absolute_path = absolute_path
        self.root_dir = absolute_path.parent
        encoded_name = urllib.parse.quote(absolute_path.name)
        self.route_path = f"/_preview/file/{encoded_name}"

    def resolve_route(self, route_path: str) -> Optional[Path]:
        prefix = "/_preview/file/"
        if not route_path.startswith(prefix):
            return None

        raw = route_path[len(prefix) :]
        if not raw:
            return None

        decoded_segments = []
        for segment in raw.split("/"):
            if not segment:
                continue
            decoded = urllib.parse.unquote(segment)
            if decoded in {"", ".", ".."}:
                return None
            decoded_segments.append(decoded)

        if not decoded_segments:
            return None

        candidate = (self.root_dir / Path(*decoded_segments)).resolve()
        if candidate == self.absolute_path:
            return candidate
        try:
            candidate.relative_to(self.root_dir)
        except ValueError:
            return None
        return candidate


def _guess_content_type(file_path: Path) -> str:
    if file_path.suffix.lower() == ".js":
        return "application/javascript; charset=utf-8"
    if file_path.suffix.lower() == ".css":
        return "text/css; charset=utf-8"
    if file_path.suffix.lower() == ".md":
        return "text/markdown; charset=utf-8"
    if file_path.suffix.lower() == ".smd":
        return "text/plain; charset=utf-8"
    content_type, _ = mimetypes.guess_type(str(file_path))
    return content_type or "application/octet-stream"


class _PreviewRequestHandler(BaseHTTPRequestHandler):
    server_version = "SoMarkPreview/1.0"

    def __init__(self, *args, vendor_dir: Path, preview_file: Optional[_PreviewFile], **kwargs):
        self._vendor_dir = vendor_dir
        self._preview_file = preview_file
        super().__init__(*args, **kwargs)

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urllib.parse.urlsplit(self.path)
        route_path = parsed.path or "/"

        if route_path == "/":
            self._serve_file(self._vendor_dir / "index.html")
            return

        if route_path.startswith("/_preview/file/"):
            if self._preview_file is None:
                self._send_text(404, "No preview file loaded.")
                return

            candidate = self._preview_file.resolve_route(route_path)
            if candidate is None:
                self._send_text(403, "Preview access denied.")
                return
            if not candidate.is_file():
                self._send_text(404, "Preview file not found.")
                return
            self._serve_file(candidate)
            return

        vendor_candidate = (self._vendor_dir / route_path.lstrip("/")).resolve()
        try:
            vendor_candidate.relative_to(self._vendor_dir)
        except ValueError:
            self._send_text(404, "Not found")
            return

        if not vendor_candidate.is_file():
            self._send_text(404, "Not found")
            return
        self._serve_file(vendor_candidate)

    def _serve_file(self, file_path: Path) -> None:
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", _guess_content_type(file_path))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, status: int, message: str) -> None:
        body = message.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class PreviewServer:
    def __init__(self, host: str, port: int, vendor_dir: Path, preview_file: Optional[_PreviewFile] = None):
        self.host = host
        self.port = port
        self._vendor_dir = vendor_dir
        self._preview_file = preview_file
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._stopped = False
        self.url = f"http://{host}:{port}"
        self.file_url = self.url

    def start(self, open_browser: bool = True) -> "PreviewServer":
        handler = partial(
            _PreviewRequestHandler,
            vendor_dir=self._vendor_dir,
            preview_file=self._preview_file,
        )
        try:
            self._server = ThreadingHTTPServer((self.host, self.port), handler)
        except OSError as exc:
            if exc.errno == 48 or "Address already in use" in str(exc):
                raise RuntimeError(f"Port {self.port} is already in use on {self.host}.") from exc
            raise RuntimeError(str(exc)) from exc

        self.port = self._server.server_port
        self.url = f"http://{self.host}:{self.port}"
        self.file_url = self.url
        if self._preview_file is not None:
            encoded_target = urllib.parse.quote(f"{self.url}{self._preview_file.route_path}", safe="")
            self.file_url = f"{self.url}?file={encoded_target}"

        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        time.sleep(0.05)

        if open_browser:
            webbrowser.open(self.file_url)
        return self

    def stop(self) -> None:
        if self._stopped:
            return
        self._stopped = True
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.stop()

    def __repr__(self) -> str:
        return f"PreviewServer(url={self.url!r}, file_url={self.file_url!r})"


class SoMarkDownPreview:
    """Local preview server for SoMarkDown files. No API key required."""

    def start(
        self,
        file: Optional[str] = None,
        host: str = "127.0.0.1",
        port: int = 7878,
        open_browser: bool = True,
    ) -> PreviewServer:
        vendor_location = _validate_vendor_location(_find_vendor_location())
        vendor_dir = vendor_location.path
        preview_file = _PreviewFile(file) if file else None
        server = PreviewServer(host=host, port=port, vendor_dir=vendor_dir, preview_file=preview_file)
        return server.start(open_browser=open_browser)
