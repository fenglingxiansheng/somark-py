import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from somark.resources.parser import DocumentParser, AsyncDocumentParser
from somark.resources._parse_core import build_parse_data, resolve_cli_file_inputs, run_limited_sync
from somark._models import ParseResponse, Task
from somark._exceptions import AuthenticationError, InvalidParamError
from somark import SoMarkWarning


def test_parse_requires_api_key():
    http = MagicMock()
    http.api_key = None
    parser = DocumentParser(http)
    with pytest.raises(AuthenticationError):
        parser.parse(file="test.pdf")


def test_parse_returns_response(tmp_path, mock_http, parse_response_data):
    # Create a dummy PDF file
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.0 test")
    mock_http.post.return_value = parse_response_data
    parser = DocumentParser(mock_http)
    response = parser.parse(file=str(pdf))
    assert isinstance(response, ParseResponse)
    assert response.ok
    assert response.task_id == "abc123"
    mock_http.post.assert_called_once()
    call_kwargs = mock_http.post.call_args
    assert "/parse/sync" in call_kwargs[0]


def test_create_returns_task(tmp_path, mock_http):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.0 test")
    mock_http.post.return_value = {
        "code": 0, "message": "任务已提交",
        "data": {"task_id": "task-xyz", "status": "queuing"}
    }
    parser = DocumentParser(mock_http)
    task = parser.create(file=str(pdf))
    assert isinstance(task, Task)
    assert task.id == "task-xyz"


def test_parse_with_extract_config(tmp_path, mock_http, parse_response_data):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.0 test")
    mock_http.post.return_value = parse_response_data
    from somark._models import ExtractConfig
    parser = DocumentParser(mock_http)
    response = parser.parse(
        file=str(pdf),
        formats=["md", "json"],
        extract_config=ExtractConfig(enable_title_level_recognition=True),
    )
    assert response.ok
    data = mock_http.post.call_args.kwargs["data"]
    assert json.loads(data["feature_config"])["enable_title_level_recognition"] is True


def test_parse_core_builds_request_data():
    from somark._models import ElementFormats, ExtractConfig

    data = build_parse_data(
        formats=["md", "json"],
        element_formats=ElementFormats(image="file", cs="image"),
        extract_config=ExtractConfig(enable_title_level_recognition=True),
    )
    assert data["output_formats"] == ["markdown", "json"]
    assert json.loads(data["element_formats"]) == {"image": "file", "cs": "image"}
    assert json.loads(data["feature_config"])["enable_title_level_recognition"] is True


def test_parse_core_resolves_cli_file_list_from_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pdf = data_dir / "a.pdf"
    pdf.write_bytes(b"%PDF-1.0 test")
    manifest = tmp_path / "files.txt"
    manifest.write_text("data/a.pdf\n\n", encoding="utf-8")

    resolved = resolve_cli_file_inputs(["direct.pdf"], str(manifest))
    assert resolved.files == ["direct.pdf", str(pdf)]
    assert resolved.is_batch is True


def test_parse_core_run_limited_preserves_order_and_reports_concurrency(monkeypatch):
    monkeypatch.setenv("SOMARK_PARSE_MAX_CONCURRENCY", "2")
    batch = run_limited_sync(["a", "b", "c"], lambda item: item.upper())
    assert batch.results == ["A", "B", "C"]
    assert batch.concurrency == 2
    assert "SOMARK_PARSE_MAX_CONCURRENCY is set to 2" in batch.warnings[0]


@pytest.mark.parametrize(
    ("requested", "sent"),
    [
        (["md"], ["markdown"]),
        (["markdown"], ["markdown"]),
        (["json"], ["json"]),
        (["zip"], ["zip"]),
    ],
)
def test_parse_accepts_supported_output_formats(tmp_path, mock_http, parse_response_data, requested, sent):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.0 test")
    mock_http.post.return_value = parse_response_data
    parser = DocumentParser(mock_http)
    parser.parse(file=str(pdf), formats=requested)
    data = mock_http.post.call_args.kwargs["data"]
    assert data["output_formats"] == sent


def test_parse_rejects_invalid_format(tmp_path, mock_http):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.0 test")
    parser = DocumentParser(mock_http)
    with pytest.raises(InvalidParamError):
        parser.parse(file=str(pdf), formats=["docx"])


@pytest.mark.parametrize("format_name", ["smd", "somarkdown"])
def test_parse_rejects_somarkdown_formats(tmp_path, mock_http, format_name):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.0 test")
    parser = DocumentParser(mock_http)
    with pytest.raises(InvalidParamError, match="Valid formats: md, markdown, json, zip"):
        parser.parse(file=str(pdf), formats=[format_name])


def test_parse_sends_cs_element_format(tmp_path, mock_http, parse_response_data):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.0 test")
    mock_http.post.return_value = parse_response_data
    from somark._models import ElementFormats
    parser = DocumentParser(mock_http)
    parser.parse(file=str(pdf), element_formats=ElementFormats(cs="image"))
    data = mock_http.post.call_args.kwargs["data"]
    assert json.loads(data["element_formats"])["cs"] == "image"


def test_parse_accepts_image_file_element_format(tmp_path, mock_http, parse_response_data):
    pdf = tmp_path / "test.pdf"
    pdf.write_bytes(b"%PDF-1.0 test")
    mock_http.post.return_value = parse_response_data
    from somark._models import ElementFormats
    parser = DocumentParser(mock_http)
    parser.parse(file=str(pdf), element_formats=ElementFormats(image="file"))
    data = mock_http.post.call_args.kwargs["data"]
    assert json.loads(data["element_formats"])["image"] == "file"


def test_parse_accepts_multiple_files(tmp_path, mock_http, parse_response_data, monkeypatch):
    monkeypatch.setenv("SOMARK_PARSE_MAX_CONCURRENCY", "1")
    files = []
    for name in ["a.pdf", "b.pdf"]:
        path = tmp_path / name
        path.write_bytes(b"%PDF-1.0 test")
        files.append(str(path))
    mock_http.post.return_value = parse_response_data
    parser = DocumentParser(mock_http)
    responses = parser.parse(file=files)
    assert [response.task_id for response in responses] == ["abc123", "abc123"]
    assert mock_http.post.call_count == 2


def test_parse_batch_attaches_concurrency_warning(tmp_path, mock_http, parse_response_data, monkeypatch):
    monkeypatch.setenv("SOMARK_PARSE_MAX_CONCURRENCY", "2")
    files = []
    for name in ["a.pdf", "b.pdf"]:
        path = tmp_path / name
        path.write_bytes(b"%PDF-1.0 test")
        files.append(str(path))
    mock_http.post.return_value = parse_response_data
    parser = DocumentParser(mock_http)
    with pytest.warns(SoMarkWarning, match="SOMARK_PARSE_MAX_CONCURRENCY is set to 2"):
        responses = parser.parse(file=files)
    assert all(response.warnings for response in responses)
    assert all("SOMARK_PARSE_MAX_CONCURRENCY is set to 2" in response.warnings[-1] for response in responses)


def test_create_accepts_multiple_files(tmp_path, mock_http):
    files = []
    for name in ["a.pdf", "b.pdf"]:
        path = tmp_path / name
        path.write_bytes(b"%PDF-1.0 test")
        files.append(str(path))
    mock_http.post.side_effect = [
        {"code": 0, "message": "", "data": {"task_id": "task-a"}},
        {"code": 0, "message": "", "data": {"task_id": "task-b"}},
    ]
    parser = DocumentParser(mock_http)
    tasks = parser.create(file=files)
    assert [task.id for task in tasks] == ["task-a", "task-b"]


def test_create_batch_attaches_concurrency_warning(tmp_path, mock_http, monkeypatch):
    monkeypatch.setenv("SOMARK_PARSE_MAX_CONCURRENCY", "2")
    files = []
    for name in ["a.pdf", "b.pdf"]:
        path = tmp_path / name
        path.write_bytes(b"%PDF-1.0 test")
        files.append(str(path))
    mock_http.post.side_effect = [
        {"code": 0, "message": "", "data": {"task_id": "task-a"}},
        {"code": 0, "message": "", "data": {"task_id": "task-b"}},
    ]
    parser = DocumentParser(mock_http)
    with pytest.warns(SoMarkWarning, match="SOMARK_PARSE_MAX_CONCURRENCY is set to 2"):
        tasks = parser.create(file=files)
    assert all("SOMARK_PARSE_MAX_CONCURRENCY is set to 2" in task.warnings[-1] for task in tasks)


def test_task_refresh_emits_api_warnings(mock_http, parse_response_data):
    mock_http.post.return_value = {**parse_response_data, "warnings": ["task warning"]}
    parser = DocumentParser(mock_http)
    task = parser.task("task-123")
    with pytest.warns(SoMarkWarning, match="task warning"):
        task.refresh()
    assert task.warnings == ["task warning"]


def test_successful_task_emits_each_warning_once(mock_http, parse_response_data):
    data = {
        **parse_response_data,
        "warnings": ["task warning", "task warning"],
        "data": {**parse_response_data["data"], "status": "success"},
    }
    mock_http.post.return_value = data
    parser = DocumentParser(mock_http)
    task = parser.task("task-123")
    with pytest.warns(SoMarkWarning) as caught:
        task.refresh()
    assert [str(item.message) for item in caught] == ["task warning"]
    assert task.result().warnings == ["task warning"]


def test_parse_reads_file_list_relative_paths_from_cwd(tmp_path, mock_http, parse_response_data, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    pdf = data_dir / "a.pdf"
    pdf.write_bytes(b"%PDF-1.0 test")
    manifest_dir = tmp_path / "lists"
    manifest_dir.mkdir()
    manifest = manifest_dir / "files.txt"
    manifest.write_text("data/a.pdf\n\n", encoding="utf-8")
    mock_http.post.return_value = parse_response_data
    parser = DocumentParser(mock_http)
    responses = parser.parse(file=str(manifest), file_list=True)
    assert len(responses) == 1
    sent_file = mock_http.post.call_args.kwargs["files"]["file"][0]
    assert sent_file == str(pdf)


def test_parse_multiple_files_prevalidates_missing(tmp_path, mock_http):
    existing = tmp_path / "a.pdf"
    existing.write_bytes(b"%PDF-1.0 test")
    parser = DocumentParser(mock_http)
    with pytest.raises(InvalidParamError, match="File not found"):
        parser.parse(file=[str(existing), str(tmp_path / "missing.pdf")])
    mock_http.post.assert_not_called()


async def test_async_parse_accepts_multiple_files(tmp_path, parse_response_data, monkeypatch):
    monkeypatch.setenv("SOMARK_PARSE_MAX_CONCURRENCY", "1")
    files = []
    for name in ["a.pdf", "b.pdf"]:
        path = tmp_path / name
        path.write_bytes(b"%PDF-1.0 test")
        files.append(str(path))
    http = MagicMock()
    http.api_key = "sk-test"
    http.post = AsyncMock(return_value=parse_response_data)
    parser = AsyncDocumentParser(http)
    responses = await parser.parse(file=files)
    assert [response.task_id for response in responses] == ["abc123", "abc123"]
    assert http.post.await_count == 2


async def test_async_create_accepts_multiple_files(tmp_path):
    files = []
    for name in ["a.pdf", "b.pdf"]:
        path = tmp_path / name
        path.write_bytes(b"%PDF-1.0 test")
        files.append(str(path))
    http = MagicMock()
    http.api_key = "sk-test"
    http.post = AsyncMock(side_effect=[
        {"code": 0, "message": "", "data": {"task_id": "task-a"}},
        {"code": 0, "message": "", "data": {"task_id": "task-b"}},
    ])
    parser = AsyncDocumentParser(http)
    tasks = await parser.create(file=files)
    assert [task.id for task in tasks] == ["task-a", "task-b"]
