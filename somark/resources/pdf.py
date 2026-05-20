from __future__ import annotations
from pathlib import Path
from typing import Optional
from somark._models import ToImagesResult

try:
    import sopdf as _sopdf
    _sopdf_import_error: ImportError | None = None
except ImportError as exc:
    _sopdf = None  # type: ignore[assignment]
    _sopdf_import_error = exc

UBUNTU_PDF_DEPENDENCY_HINT = (
    "On minimal Docker/Ubuntu images, PDF rendering may also require system libraries: "
    "apt-get install -y --no-install-recommends libxcb1 libgl1 libglib2.0-0"
)


def pdf_dependency_error(error: BaseException | None = None) -> str:
    message = "sopdf is not available. Run: pip install somark."
    if error:
        message += f" Import error: {error}."
    return f"{message} {UBUNTU_PDF_DEPENDENCY_HINT}"


class PDFProcessor:
    """Local PDF processing using sopdf. No API key required."""

    def to_images(
        self,
        file: str,
        out: str = "./",
        filename_format: Optional[str] = None,
        dpi: int = 150,
    ) -> ToImagesResult:
        if _sopdf is None:
            return ToImagesResult(ok=False, error=pdf_dependency_error(_sopdf_import_error))

        try:
            out_dir = Path(out)
            out_dir.mkdir(parents=True, exist_ok=True)
            base_name = Path(file).stem
            fmt = filename_format or "{name}.page-{n}.png"

            with _sopdf.open(file) as doc:
                images = _sopdf.render_pages(doc.pages, dpi=dpi, parallel=True)

            files = []
            for i, img_bytes in enumerate(images):
                out_name = fmt.format(name=base_name, n=i + 1)
                out_path = out_dir / out_name
                out_path.write_bytes(img_bytes)
                files.append(str(out_path))

            return ToImagesResult(ok=True, files=files)
        except (ImportError, OSError) as exc:
            return ToImagesResult(ok=False, error=pdf_dependency_error(exc))
