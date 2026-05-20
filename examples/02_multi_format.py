"""
02_multi_format.py — Multi-format export in a single parse call

Demonstrates requesting md + json in one call, with custom element formats.

Run:
    python examples/02_multi_format.py

Requires: SOMARK_API_KEY env var (or ~/.somark/config.toml)
"""

import sys
from pathlib import Path

from somark import SoMark

DATA_DIR = Path(__file__).parent / "data"
FILE = DATA_DIR / "5115_Attention_Guided_Alignmen.pdf"


def main() -> None:
    client = SoMark()

    print(f"Parsing: {FILE}")
    print("Requesting formats: md + json\n")

    response = client.parser.parse(
        file=str(FILE),
        formats=["md", "json"],
        element_formats={
            "formula": "latex",
            "table": "markdown",
        },
    )

    print(f"Pages parsed: {response.pages}")
    print(f"File type:    {response.file_type}")
    print()

    # Show markdown snippet
    if response.md:
        print("--- Markdown (first 300 chars) ---")
        print(response.md[:300])
        print("...\n")

    # Show JSON structure (top-level keys)
    if response.json_output:
        keys = list(response.json_output.keys())
        print("--- JSON output top-level keys ---")
        print(keys)
        print()

    # Save both formats
    out_dir = Path(__file__).parent
    md_path = out_dir / "output_02.md"
    json_path = out_dir / "output_02.json"

    response.save(str(md_path), format="md")
    response.save(str(json_path), format="json")

    print(f"Saved markdown to: {md_path}")
    print(f"Saved JSON to:     {json_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
