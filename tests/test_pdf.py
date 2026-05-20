from pathlib import Path
from unittest.mock import patch, MagicMock
import somark.resources.pdf as pdf_module
from somark.resources.pdf import PDFProcessor

# Minimal PNG header bytes used as fake rendered-page output
_FAKE_PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 8


def _make_mock_sopdf(page_count: int = 2):
    """Return a mock sopdf module that simulates rendering ``page_count`` pages."""
    mock_doc = MagicMock()
    mock_doc.pages = [MagicMock() for _ in range(page_count)]
    mock_doc.__enter__ = MagicMock(return_value=mock_doc)
    mock_doc.__exit__ = MagicMock(return_value=False)

    mock_sopdf = MagicMock()
    mock_sopdf.open.return_value = mock_doc
    mock_sopdf.render_pages.return_value = [_FAKE_PNG] * page_count
    return mock_sopdf


def test_pdf_no_sopdf(tmp_path):
    """Returns error result when sopdf is not installed."""
    pdf_file = tmp_path / "test.pdf"
    pdf_file.write_bytes(b"%PDF test")
    import_error = ImportError("libGL.so.1: cannot open shared object file")
    with patch.object(pdf_module, "_sopdf", None):
        with patch.object(pdf_module, "_sopdf_import_error", import_error):
            result = PDFProcessor().to_images(str(pdf_file), out=str(tmp_path))
    assert not result.ok
    assert "sopdf" in result.error
    assert "libxcb1 libgl1 libglib2.0-0" in result.error


def test_pdf_native_library_error_is_readable(tmp_path):
    """Native-library failures include the Ubuntu package hint."""
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.0 test")
    mock_sopdf = _make_mock_sopdf(page_count=1)
    mock_sopdf.open.side_effect = OSError("libxcb.so.1: cannot open shared object file")

    with patch.object(pdf_module, "_sopdf", mock_sopdf):
        result = PDFProcessor().to_images(str(pdf_file), out=str(tmp_path))

    assert not result.ok
    assert "libxcb.so.1" in result.error
    assert "apt-get install" in result.error


def test_pdf_to_images_success(tmp_path):
    """Successful conversion returns ok=True and writes one PNG per page."""
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.0 test")
    mock_sopdf = _make_mock_sopdf(page_count=2)

    with patch.object(pdf_module, "_sopdf", mock_sopdf):
        result = PDFProcessor().to_images(str(pdf_file), out=str(tmp_path))

    assert result.ok is True
    assert len(result.files) == 2
    for f in result.files:
        assert f.endswith(".png")
        assert Path(f).exists()
        assert Path(f).read_bytes() == _FAKE_PNG


def test_pdf_to_images_uses_parallel(tmp_path):
    """render_pages is always called with parallel=True."""
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.0 test")
    mock_sopdf = _make_mock_sopdf(page_count=1)

    with patch.object(pdf_module, "_sopdf", mock_sopdf):
        PDFProcessor().to_images(str(pdf_file), out=str(tmp_path))

    _, kwargs = mock_sopdf.render_pages.call_args
    assert kwargs.get("parallel") is True


def test_pdf_to_images_custom_dpi(tmp_path):
    """render_pages receives the dpi value passed by the caller."""
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.0 test")
    mock_sopdf = _make_mock_sopdf(page_count=1)

    with patch.object(pdf_module, "_sopdf", mock_sopdf):
        PDFProcessor().to_images(str(pdf_file), out=str(tmp_path), dpi=300)

    _, kwargs = mock_sopdf.render_pages.call_args
    assert kwargs.get("dpi") == 300


def test_pdf_to_images_filename_format(tmp_path):
    """Custom filename_format applies {name} and {n} placeholders correctly."""
    pdf_file = tmp_path / "myreport.pdf"
    pdf_file.write_bytes(b"%PDF-1.0 test")
    mock_sopdf = _make_mock_sopdf(page_count=2)

    with patch.object(pdf_module, "_sopdf", mock_sopdf):
        result = PDFProcessor().to_images(
            str(pdf_file),
            out=str(tmp_path),
            filename_format="out-{name}-p{n}.png",
        )

    names = [Path(f).name for f in result.files]
    assert names[0] == "out-myreport-p1.png"
    assert names[1] == "out-myreport-p2.png"


def test_pdf_to_images_creates_output_dir(tmp_path):
    """Output directory is created automatically if it does not exist."""
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_bytes(b"%PDF-1.0 test")
    new_dir = tmp_path / "deep" / "nested" / "output"
    mock_sopdf = _make_mock_sopdf(page_count=1)

    with patch.object(pdf_module, "_sopdf", mock_sopdf):
        result = PDFProcessor().to_images(str(pdf_file), out=str(new_dir))

    assert new_dir.exists()
    assert result.ok is True
