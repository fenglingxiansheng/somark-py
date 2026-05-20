"""
01_basic_parse.py — Basic synchronous PDF parsing

Demonstrates the simplest path: PDF → markdown via parser.parse()

Run:
    python examples/01_basic_parse.py

Requires: SOMARK_API_KEY env var (or ~/.somark/config.toml)
"""

import os
import sys
from pathlib import Path

from somark import SoMark

DATA_DIR = Path(__file__).parent / "data"
FILE = DATA_DIR / "2010.02399v1.pdf"


def main() -> None:
    client = SoMark()

    print(f"Parsing: {FILE}")
    print("Sending to SoMark API (sync)...\n")

    response = client.parser.parse(
        file=str(FILE),
        formats=["md"],
    )

    print(f"Pages parsed: {response.pages}")
    print(f"File type:    {response.file_type}")
    print()

    if response.md:
        preview = response.md[:500]
        print("--- Markdown preview (first 500 chars) ---")
        print(preview)
        print("...")
        print()

    out_path = Path(__file__).parent / "output_01.md"
    response.save(str(out_path), format="md")
    print(f"Saved to: {out_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
