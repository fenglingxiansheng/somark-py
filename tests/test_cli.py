import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock

runner = CliRunner()


def combined_output(result):
    parts = [getattr(result, "output", "")]
    stderr_bytes = getattr(result, "stderr_bytes", None)
    if stderr_bytes:
        parts.append(stderr_bytes.decode(errors="replace"))
    return "".join(parts)


def get_app():
    from somark.cli.main import app
    return app


def make_parse_task(response, task_id="test-task"):
    task = MagicMock()
    task.id = task_id
    task.wait.return_value = response
    return task


def test_version():
    app = get_app()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "somark" in result.output


def test_help():
    app = get_app()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "parse" in result.output
    assert "usage" in result.output


def test_parse_help_format_flags():
    app = get_app()
    result = runner.invoke(app, ["parse", "--help"])
    assert result.exit_code == 0
    assert "md,markdown,json,zip" in result.output
    assert "smd" not in result.output
    assert "--image-fmt" in result.output
    assert "--formula-fmt" in result.output
    assert "--table-fmt" in result.output
    assert "--cs-fmt" in result.output
    assert "--image " not in result.output
    assert "--formula " not in result.output
    assert "--cs " not in result.output


@pytest.mark.parametrize(
    "args",
    [
        ["parse", "example.pdf", "--image", "base64"],
        ["parse", "example.pdf", "--formula", "latex"],
        ["parse", "example.pdf", "--cs", "image"],
    ],
)
def test_parse_old_format_flags_rejected(args):
    app = get_app()
    result = runner.invoke(app, args)
    assert result.exit_code == 2
    assert "No such option" in result.output or "No such command" in result.output


def test_config_set_get(tmp_path):
    app = get_app()
    with patch("somark._config.CONFIG_FILE", tmp_path / "config.toml"):
        result = runner.invoke(app, ["config", "set", "api_key", "sk-test"])
        assert result.exit_code == 0
        assert "sk-test" not in result.output
        result2 = runner.invoke(app, ["config", "get", "api_key"])
        assert result2.exit_code == 0
        assert "sk-test" not in result2.output
        assert "api_key = ***" in result2.output


def test_config_get_show_reveals_api_key(tmp_path):
    app = get_app()
    with patch("somark._config.CONFIG_FILE", tmp_path / "config.toml"):
        result = runner.invoke(app, ["config", "set", "api_key", "sk-test", "--show"])
        assert result.exit_code == 0
        assert "sk-test" in result.output

        result2 = runner.invoke(app, ["config", "get", "api_key", "--show"])
        assert result2.exit_code == 0
        assert "sk-test" in result2.output


def test_config_list_masks_api_key_by_default(tmp_path):
    app = get_app()
    with patch("somark._config.CONFIG_FILE", tmp_path / "config.toml"):
        runner.invoke(app, ["config", "set", "api_key", "sk-test"])

        result = runner.invoke(app, ["config", "list"])
        assert result.exit_code == 0
        assert "sk-test" not in result.output
        assert "api_key = ***" in result.output

        result2 = runner.invoke(app, ["config", "list", "--show"])
        assert result2.exit_code == 0
        assert "sk-test" in result2.output


def test_usage_with_mock():
    app = get_app()
    mock_usage = MagicMock()
    mock_usage.remaining_paid_pages = 1000
    mock_usage.remaining_free_pages_today = 50
    mock_usage.remaining_free_pages_this_month = 200
    mock_usage.dashboard_url = "https://somark.tech/workbench"
    mock_usage.model_dump.return_value = {
        "remaining_paid_pages": 1000,
        "remaining_free_pages_today": 50,
        "remaining_free_pages_this_month": 200,
    }

    mock_client = MagicMock()
    mock_client.usage.get.return_value = mock_usage

    with patch("somark.cli.main._make_client", return_value=mock_client):
        result = runner.invoke(app, ["usage", "--format", "text"])
    assert result.exit_code == 0
    assert "1,000" in result.output or "1000" in result.output


def test_parse_task_wait_saves_output(tmp_path, parse_response_data):
    from somark._models import Task

    app = get_app()
    output = tmp_path / "task.md"
    task_data = {
        **parse_response_data,
        "data": {
            **parse_response_data["data"],
            "status": "success",
            "file_name": "large.pdf",
        },
    }
    mock_client = MagicMock()
    mock_client.parser.task.return_value = Task("task-123", lambda task_id: task_data)

    with patch("somark.cli.main._make_client", return_value=mock_client), patch("time.sleep"):
        result = runner.invoke(app, ["parse", "--task-id", "task-123", "--wait", "--out", str(output)])

    assert result.exit_code == 0
    assert output.read_text() == parse_response_data["data"]["result"]["outputs"]["markdown"]
    mock_client.parser.task.assert_called_once_with("task-123")


def test_parse_single_format_without_out_writes_stdout(tmp_path, parse_response_data):
    from somark._models import ParseResponse

    app = get_app()
    input_file = tmp_path / "input.png"
    input_file.write_bytes(b"png")
    response = ParseResponse.from_api(parse_response_data)
    response.source_file_name = input_file.name
    mock_client = MagicMock()
    mock_client.parser.create.return_value = make_parse_task(response)

    with patch("somark.cli.main._make_client", return_value=mock_client):
        result = runner.invoke(app, ["parse", str(input_file), "--formats", "md"])

    assert result.exit_code == 0
    assert response.md in result.output
    assert not (tmp_path / "input.md").exists()


def test_parse_multiple_formats_without_out_errors(tmp_path):
    app = get_app()
    input_file = tmp_path / "input.png"
    input_file.write_bytes(b"png")
    mock_client = MagicMock()

    with patch("somark.cli.main._make_client", return_value=mock_client):
        result = runner.invoke(app, ["parse", str(input_file), "--formats", "md,json"])

    assert result.exit_code == 1
    assert "multiple formats require --out to be an existing directory" in combined_output(result)
    mock_client.parser.create.assert_not_called()


def test_parse_existing_directory_writes_all_formats(tmp_path, parse_response_data):
    from somark._models import ParseResponse

    app = get_app()
    input_file = tmp_path / "input.png"
    input_file.write_bytes(b"png")
    output_dir = tmp_path / "results"
    output_dir.mkdir()
    response = ParseResponse.from_api(parse_response_data)
    response.source_file_name = input_file.name
    mock_client = MagicMock()
    mock_client.parser.create.return_value = make_parse_task(response)

    with patch("somark.cli.main._make_client", return_value=mock_client):
        result = runner.invoke(app, ["parse", str(input_file), "--formats", "md,json", "--out", str(output_dir)])

    assert result.exit_code == 0
    assert (output_dir / "input.md").read_text() == response.md
    assert (output_dir / "input.json").exists()


def test_parse_single_format_out_file_writes_file(tmp_path, parse_response_data):
    from somark._models import ParseResponse

    app = get_app()
    input_file = tmp_path / "input.png"
    input_file.write_bytes(b"png")
    output_file = tmp_path / "result.md"
    response = ParseResponse.from_api(parse_response_data)
    mock_client = MagicMock()
    mock_client.parser.create.return_value = make_parse_task(response)

    with patch("somark.cli.main._make_client", return_value=mock_client):
        result = runner.invoke(app, ["parse", str(input_file), "--formats", "md", "--out", str(output_file)])

    assert result.exit_code == 0
    assert output_file.read_text() == response.md


def test_parse_multiple_formats_out_file_errors(tmp_path):
    app = get_app()
    input_file = tmp_path / "input.png"
    input_file.write_bytes(b"png")
    output_file = tmp_path / "result.md"
    mock_client = MagicMock()

    with patch("somark.cli.main._make_client", return_value=mock_client):
        result = runner.invoke(app, ["parse", str(input_file), "--formats", "md,json", "--out", str(output_file)])

    assert result.exit_code == 1
    assert "multiple formats require --out to be an existing directory" in combined_output(result)
    mock_client.parser.create.assert_not_called()


def test_parse_missing_output_directory_errors(tmp_path):
    app = get_app()
    input_file = tmp_path / "input.png"
    input_file.write_bytes(b"png")
    mock_client = MagicMock()
    missing_dir = tmp_path / "missing"

    with patch("somark.cli.main._make_client", return_value=mock_client):
        result = runner.invoke(app, ["parse", str(input_file), "--formats", "md", "--out", str(missing_dir) + "/"])

    assert result.exit_code == 1
    assert "output directory does not exist" in combined_output(result)
    mock_client.parser.create.assert_not_called()


def test_parse_missing_output_parent_errors(tmp_path):
    app = get_app()
    input_file = tmp_path / "input.png"
    input_file.write_bytes(b"png")
    mock_client = MagicMock()

    with patch("somark.cli.main._make_client", return_value=mock_client):
        result = runner.invoke(
            app,
            ["parse", str(input_file), "--formats", "md", "--out", str(tmp_path / "missing" / "result.md")],
        )

    assert result.exit_code == 1
    assert "output parent directory does not exist" in combined_output(result)
    mock_client.parser.create.assert_not_called()


def test_parse_file_list_batch_outputs_and_warns(tmp_path, parse_response_data, monkeypatch):
    from somark._models import ParseResponse
    from somark import SoMarkWarning

    monkeypatch.chdir(tmp_path)
    app = get_app()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    first = data_dir / "a.pdf"
    second = data_dir / "b.pdf"
    first.write_bytes(b"%PDF-1.0 a")
    second.write_bytes(b"%PDF-1.0 b")
    manifest_dir = tmp_path / "lists"
    manifest_dir.mkdir()
    manifest = manifest_dir / "files.txt"
    manifest.write_text("data/a.pdf\ndata/b.pdf\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    response = ParseResponse.from_api(parse_response_data)
    mock_client = MagicMock()
    mock_client.parser.create.side_effect = [make_parse_task(response, "task-a"), make_parse_task(response, "task-b")]
    monkeypatch.setenv("SOMARK_PARSE_MAX_CONCURRENCY", "2")

    from somark._warnings import emit_warnings

    def parse_batch(**kwargs):
        emit_warnings(["sdk concurrency warning"])
        return make_parse_task(response, Path(kwargs["file"]).stem)

    mock_client.parser.create.side_effect = parse_batch

    with patch("somark.cli.main._make_client", return_value=mock_client):
        with pytest.warns(SoMarkWarning, match="sdk concurrency warning"):
            result = runner.invoke(app, ["parse", "--file-list", str(manifest), "--out", str(output_dir)])

    assert result.exit_code == 0
    assert "total=2 success=2 failed=0" in result.output
    assert (output_dir / "a.md").read_text() == response.md
    assert (output_dir / "b.md").read_text() == response.md
    assert mock_client.parser.create.call_count == 2
    assert {call.kwargs["file"] for call in mock_client.parser.create.call_args_list} == {str(first), str(second)}


def test_no_warnings_suppresses_cli_warnings(tmp_path, parse_response_data, monkeypatch):
    from somark._models import ParseResponse
    from somark import SoMarkWarning
    import warnings

    monkeypatch.chdir(tmp_path)
    app = get_app()
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    first = data_dir / "a.pdf"
    second = data_dir / "b.pdf"
    first.write_bytes(b"%PDF-1.0 a")
    second.write_bytes(b"%PDF-1.0 b")
    manifest = tmp_path / "files.txt"
    manifest.write_text("data/a.pdf\ndata/b.pdf\n", encoding="utf-8")
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    response = ParseResponse.from_api(parse_response_data)
    mock_client = MagicMock()
    mock_client.parser.create.side_effect = [make_parse_task(response, "task-a"), make_parse_task(response, "task-b")]
    monkeypatch.setenv("SOMARK_PARSE_MAX_CONCURRENCY", "2")

    from somark._warnings import emit_warnings

    def parse_batch(**kwargs):
        emit_warnings(["hidden sdk warning"])
        return make_parse_task(response, Path(kwargs["file"]).stem)

    mock_client.parser.create.side_effect = parse_batch

    with patch("somark.cli.main._make_client", return_value=mock_client), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", SoMarkWarning)
        result = runner.invoke(app, ["--no-warnings", "parse", "--file-list", str(manifest), "--out", str(output_dir)])

    assert result.exit_code == 0
    assert not [item for item in caught if issubclass(item.category, SoMarkWarning)]
    assert "hidden sdk warning" not in combined_output(result)


def test_parse_batch_prevalidates_missing_and_exits_nonzero(tmp_path, parse_response_data):
    from somark._exceptions import InvalidParamError

    app = get_app()
    existing = tmp_path / "a.pdf"
    missing = tmp_path / "missing.pdf"
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    existing.write_bytes(b"%PDF-1.0 a")
    mock_client = MagicMock()

    with patch("somark.cli.main._make_client", return_value=mock_client):
        result = runner.invoke(app, ["parse", str(existing), str(missing), "--out", str(output_dir)])

    assert result.exit_code == 1
    assert "File not found" in result.output
    assert "missing" in combined_output(result)
    assert "Summary:" not in result.output
    assert not (output_dir / "a.md").exists()
    mock_client.parser.create.assert_not_called()


def test_parse_batch_without_out_errors(tmp_path):
    app = get_app()
    first = tmp_path / "a.pdf"
    second = tmp_path / "b.pdf"
    first.write_bytes(b"%PDF-1.0 a")
    second.write_bytes(b"%PDF-1.0 b")
    mock_client = MagicMock()

    with patch("somark.cli.main._make_client", return_value=mock_client):
        result = runner.invoke(app, ["parse", str(first), str(second)])

    assert result.exit_code == 1
    assert "batch parse requires --out to be an existing directory" in combined_output(result)
    mock_client.parser.create.assert_not_called()


def test_parse_batch_missing_output_dir_errors(tmp_path):
    app = get_app()
    first = tmp_path / "a.pdf"
    second = tmp_path / "b.pdf"
    first.write_bytes(b"%PDF-1.0 a")
    second.write_bytes(b"%PDF-1.0 b")
    mock_client = MagicMock()

    with patch("somark.cli.main._make_client", return_value=mock_client):
        result = runner.invoke(app, ["parse", str(first), str(second), "--out", str(tmp_path / "out")])

    assert result.exit_code == 1
    assert "batch parse requires --out to be an existing directory" in combined_output(result)
    mock_client.parser.create.assert_not_called()


def test_doctor_fix_replaces_placeholder_vendor_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    viewer_dir = tmp_path / "vendor" / "somarkdown-viewer"
    viewer_dir.mkdir(parents=True)
    (viewer_dir / ".gitkeep").write_text("")

    def fake_run(cmd, check=True):
        if cmd[:3] == ["git", "clone", "--depth"]:
            viewer_dir.mkdir(parents=True, exist_ok=True)
            (viewer_dir / "get_latest_smd.sh").write_text("#!/usr/bin/env bash\n")
        return MagicMock()

    app = get_app()
    with patch("subprocess.run", side_effect=fake_run) as run_mock:
        result = runner.invoke(app, ["doctor", "fix"])

    assert result.exit_code == 0
    assert "Preview assets repaired" in result.output
    assert any(call.args[0][0] == "git" and call.args[0][1] == "clone" for call in run_mock.call_args_list)
    assert any(call.args[0][0] == "bash" for call in run_mock.call_args_list)
