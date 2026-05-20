import io
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from somark.resources import preview as preview_module
from somark.resources.preview import SoMarkDownPreview, _PreviewFile, _PreviewRequestHandler

runner = CliRunner()


def _write_vendor_files(root_dir: Path) -> None:
    viewer_dir = root_dir / "vendor" / "somarkdown-viewer"
    (viewer_dir / "lib").mkdir(parents=True, exist_ok=True)
    (viewer_dir / "style").mkdir(parents=True, exist_ok=True)
    (viewer_dir / "index.html").write_text("<!doctype html><html><body>viewer</body></html>", encoding="utf-8")
    (viewer_dir / "lib" / "viewer.js").write_text('console.log("viewer")', encoding="utf-8")
    (viewer_dir / "style" / "viewer.css").write_text("body { color: black; }", encoding="utf-8")


def test_vendor_locator_prefers_package_assets(tmp_path, monkeypatch):
    package_root = tmp_path / "package"
    cwd_root = tmp_path / "cwd"
    _write_vendor_files(package_root)
    _write_vendor_files(cwd_root)
    monkeypatch.chdir(cwd_root)
    monkeypatch.setattr(preview_module, "_package_vendor_dir", lambda: package_root / "vendor" / "somarkdown-viewer")

    location = preview_module._find_vendor_location()

    assert location is not None
    assert location.path == (package_root / "vendor" / "somarkdown-viewer").resolve()
    assert location.source == "package"


def test_vendor_locator_uses_cwd_development_fallback(tmp_path, monkeypatch):
    _write_vendor_files(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(preview_module, "_package_vendor_dir", lambda: tmp_path / "missing-package-viewer")

    location = preview_module._find_vendor_location()

    assert location is not None
    assert location.path == (tmp_path / "vendor" / "somarkdown-viewer").resolve()
    assert location.source == "development"


def test_package_vendor_validation_does_not_suggest_doctor_fix(tmp_path, monkeypatch):
    package_viewer = tmp_path / "package" / "vendor" / "somarkdown-viewer"
    package_viewer.mkdir(parents=True)
    monkeypatch.setattr(preview_module, "_package_vendor_dir", lambda: package_viewer)

    with pytest.raises(RuntimeError, match="Reinstall the package"):
        preview_module._validate_vendor_location(preview_module._find_vendor_location())


def _invoke_handler(vendor_dir: Path, preview_file: Optional[_PreviewFile], request_path: str):
    handler = object.__new__(_PreviewRequestHandler)
    handler.path = request_path
    handler._vendor_dir = vendor_dir
    handler._preview_file = preview_file
    handler.wfile = io.BytesIO()
    handler._status = None
    handler._headers = {}

    def send_response(status_code, message=None):
        handler._status = status_code

    def send_header(key, value):
        handler._headers[key] = value

    def end_headers():
        return None

    handler.send_response = send_response
    handler.send_header = send_header
    handler.end_headers = end_headers
    handler.do_GET()
    return handler._status, handler._headers, handler.wfile.getvalue()


def test_preview_resource_errors_when_vendor_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(preview_module, "_package_vendor_dir", lambda: tmp_path / "missing-package-viewer")

    resource = SoMarkDownPreview()
    with pytest.raises(RuntimeError, match="somark doctor fix"):
        resource.start(open_browser=False)


def test_preview_resource_serves_files_from_allowed_tree(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_vendor_files(tmp_path)

    docs_dir = tmp_path / "docs"
    assets_dir = docs_dir / "assets"
    assets_dir.mkdir(parents=True)
    main_file = docs_dir / "main.smd"
    main_file.write_text("# Preview\n![asset](assets/info.txt)\n", encoding="utf-8")
    (assets_dir / "info.txt").write_text("asset payload", encoding="utf-8")
    (tmp_path / "outside.txt").write_text("outside payload", encoding="utf-8")

    viewer_dir = tmp_path / "vendor" / "somarkdown-viewer"
    preview_file = _PreviewFile(str(main_file))

    status, headers, body = _invoke_handler(viewer_dir, preview_file, "/")
    assert status == 200
    assert "viewer" in body.decode("utf-8")

    status, headers, body = _invoke_handler(viewer_dir, preview_file, "/lib/viewer.js")
    assert status == 200
    assert "application/javascript" in headers["Content-Type"]

    status, headers, body = _invoke_handler(viewer_dir, preview_file, preview_file.route_path)
    assert status == 200
    assert "# Preview" in body.decode("utf-8")

    status, headers, body = _invoke_handler(viewer_dir, preview_file, "/_preview/file/assets/info.txt")
    assert status == 200
    assert body.decode("utf-8") == "asset payload"

    status, headers, body = _invoke_handler(viewer_dir, preview_file, "/_preview/file/%2E%2E/outside.txt")
    assert status == 403


def test_preview_resource_rejects_unsupported_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_vendor_files(tmp_path)
    bad_file = tmp_path / "notes.txt"
    bad_file.write_text("bad", encoding="utf-8")

    resource = SoMarkDownPreview()
    with pytest.raises(RuntimeError, match=r"Use \.md or \.smd"):
        resource.start(file=str(bad_file), open_browser=False)


def test_preview_resource_reports_port_conflicts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_vendor_files(tmp_path)
    resource = SoMarkDownPreview()

    conflict_error = OSError("Address already in use")
    conflict_error.errno = 48

    with patch.object(preview_module, "ThreadingHTTPServer", side_effect=conflict_error):
        with pytest.raises(RuntimeError, match="already in use"):
            resource.start(port=7878, open_browser=False)


def test_preview_cli_exits_non_zero_when_vendor_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(preview_module, "_package_vendor_dir", lambda: tmp_path / "missing-package-viewer")
    from somark.cli.main import app

    result = runner.invoke(app, ["preview", "--no-open"])
    assert result.exit_code == 1
    assert "somark doctor fix" in result.output


def test_preview_resource_does_not_open_browser_when_disabled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_vendor_files(tmp_path)
    main_file = tmp_path / "doc.md"
    main_file.write_text("# Hello", encoding="utf-8")

    resource = SoMarkDownPreview()
    fake_server = type(
        "FakeHTTPServer",
        (),
        {
            "__init__": lambda self, *args, **kwargs: setattr(self, "server_port", 9123),
            "serve_forever": lambda self: None,
            "shutdown": lambda self: None,
            "server_close": lambda self: None,
        },
    )

    with patch.object(preview_module, "ThreadingHTTPServer", fake_server), patch("webbrowser.open") as open_mock:
        server = resource.start(file=str(main_file), port=0, open_browser=False)
        server.stop()

    open_mock.assert_not_called()
