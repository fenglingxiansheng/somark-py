import pytest
from somark._models import ParseResponse, Usage, ExtractConfig, ElementFormats, ToImagesResult


def test_parse_response_from_api(parse_response_data):
    r = ParseResponse.from_api(parse_response_data)
    assert r.ok is True
    assert r.code == 0
    assert r.task_id == "abc123"
    assert r.pages == 5
    assert r.md == "# Hello World\n\nThis is a test."
    assert r.file_type == ".pdf"
    assert r.warnings == []
    assert r.source_file_name == "test.pdf"


def test_parse_response_reads_api_warnings(parse_response_data):
    data = {
        **parse_response_data,
        "warnings": ["top warning", "", "top warning", 123],
    }
    r = ParseResponse.from_api(data)
    assert r.warnings == ["top warning"]


def test_parse_response_ignores_malformed_api_warnings(parse_response_data):
    data = {**parse_response_data, "warnings": {"message": "ignored"}}
    r = ParseResponse.from_api(data)
    assert r.warnings == []


def test_parse_response_save(tmp_path, parse_response_data):
    r = ParseResponse.from_api(parse_response_data)
    out = tmp_path / "output.md"
    r.save(str(out))
    assert out.read_text() == r.md


def test_parse_response_save_json(tmp_path, parse_response_data):
    import json
    r = ParseResponse.from_api(parse_response_data)
    out = tmp_path / "output.json"
    r.save(str(out), format="json")
    data = json.loads(out.read_text())
    assert data == r.json_output


def test_parse_response_save_zip_downloads_url(tmp_path, parse_response_data, monkeypatch):
    data = {
        **parse_response_data,
        "data": {
            **parse_response_data["data"],
            "result": {
                **parse_response_data["data"]["result"],
                "outputs": {
                    **parse_response_data["data"]["result"]["outputs"],
                    "zip": "https://example.com/output.zip",
                },
            },
        },
    }
    r = ParseResponse.from_api(data)
    out = tmp_path / "output.zip"
    zip_bytes = b"PK\x03\x04zip payload"

    class FakeResponse:
        def raise_for_status(self):
            return None

        def iter_bytes(self):
            yield zip_bytes

    class FakeStream:
        def __enter__(self):
            return FakeResponse()

        def __exit__(self, *args):
            return None

    def fake_stream(method, url, *, follow_redirects, timeout):
        assert method == "GET"
        assert url == "https://example.com/output.zip"
        assert follow_redirects is True
        assert timeout == 60.0
        return FakeStream()

    monkeypatch.setattr("httpx.stream", fake_stream)
    r.save(str(out), format="zip")
    assert out.read_bytes() == zip_bytes


def test_parse_response_save_directory_multiple_formats(tmp_path, parse_response_data):
    r = ParseResponse.from_api(parse_response_data)
    r.save(str(tmp_path), format=["md", "json"])
    assert (tmp_path / "test.md").read_text() == r.md
    assert (tmp_path / "test.json").exists()


def test_parse_response_save_multiple_formats_requires_directory(tmp_path, parse_response_data):
    r = ParseResponse.from_api(parse_response_data)
    with pytest.raises(ValueError, match="multiple formats require --out to be an existing directory"):
        r.save(str(tmp_path / "output.md"), format=["md", "json"])


def test_parse_response_save_missing_parent_raises(tmp_path, parse_response_data):
    r = ParseResponse.from_api(parse_response_data)
    with pytest.raises(ValueError, match="output parent directory does not exist"):
        r.save(str(tmp_path / "missing" / "output.md"), format="md")


@pytest.mark.parametrize("format_name", ["smd", "somarkdown"])
def test_parse_response_save_somarkdown_raises(tmp_path, parse_response_data, format_name):
    r = ParseResponse.from_api(parse_response_data)
    with pytest.raises(ValueError, match="Unsupported output format"):
        r.save(str(tmp_path / "output.smd"), format=format_name)


def test_usage_from_api(usage_response_data):
    u = Usage.from_api(usage_response_data)
    assert u.ok is True
    assert u.remaining_paid_pages == 104410
    assert u.remaining_free_pages_today == 295
    assert u.remaining_free_pages_this_month == 578
    assert "somark.tech" in u.dashboard_url


def test_usage_reads_api_warnings(usage_response_data):
    data = {**usage_response_data, "warnings": ["usage warning"]}
    u = Usage.from_api(data)
    assert u.warnings == ["usage warning"]


def test_extract_config_defaults():
    ec = ExtractConfig()
    assert ec.enable_inline_image is True
    assert ec.enable_title_level_recognition is False


def test_element_formats_model_dump():
    ef = ElementFormats(formula="latex", table=None)
    d = ef.model_dump()
    assert d == {"formula": "latex"}  # None values excluded


def test_to_images_result():
    r = ToImagesResult(ok=True, files=["a.png", "b.png"])
    assert r.ok
    assert len(r.files) == 2
