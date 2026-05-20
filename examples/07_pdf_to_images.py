"""
07_pdf_to_images.py — Convert PDF pages to images locally

Uses pdf.to_images() which renders locally via sopdf.
No API key required for this operation.

Run:
    python examples/07_pdf_to_images.py

PDF support is included with somark.
"""

import sys
from pathlib import Path

from somark import SoMark

DATA_DIR = Path(__file__).parent / "data"
FILE = DATA_DIR / "5115_Attention_Guided_Alignmen.pdf"
OUT_DIR = Path(__file__).parent / "output_07_images"


def main() -> None:
    # No API key needed for local PDF rendering
    client = SoMark()

    print("Converting PDF pages to images...")
    print(f"Input:  {FILE}")
    print(f"Output: {OUT_DIR}")
    print()

    OUT_DIR.mkdir(exist_ok=True)

    result = client.pdf.to_images(
        file=str(FILE),
        out=str(OUT_DIR),
        dpi=150,
        filename_format="{name}-page-{n}.png",
    )

    if not result.ok:
        print(f"Error converting PDF: {result.error}", file=sys.stderr)
        sys.exit(1)

    print(f"Rendered {len(result.files)} page(s):")
    for f in result.files:
        print(f"  {f}")


if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        if "sopdf" in str(e):
            print(f"Error: {e}", file=sys.stderr)
            print("\nHint: install somark again:", file=sys.stderr)
            print("  pip install somark", file=sys.stderr)
        else:
            raise
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
