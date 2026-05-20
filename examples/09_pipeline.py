"""
09_pipeline.py — End-to-end pipeline: parse → save Markdown → preview

Demonstrates a realistic workflow:
  1. Parse a Chinese exam image with SoMark API
  2. Save the result as a .md file
  3. Start a local preview server and open in browser

Run:
    python examples/09_pipeline.py

Requires: SOMARK_API_KEY env var (or ~/.somark/config.toml)
Note: Preview server requires the somarkdown-viewer vendor files.
"""

import sys
from pathlib import Path

from somark import SoMark

DATA_DIR = Path(__file__).parent / "data"
IMAGE_FILE = DATA_DIR / "中文试卷-page.png"


def main() -> None:
    client = SoMark()

    # Step 1: Parse image
    print("Step 1: Parsing Chinese exam image...")
    print(f"File: {IMAGE_FILE}")
    print()

    response = client.parser.parse(
        file=str(IMAGE_FILE),
        formats=["md"],
    )

    print(f"Parsed {response.pages} page(s)")
    print()

    # Step 2: Save outputs
    out_dir = Path(__file__).parent
    md_path = out_dir / "output_09.md"

    response.save(str(md_path), format="md")
    print(f"Step 2: Saved MD to: {md_path}")

    print()

    # Step 3: Preview server
    print("Step 3: Starting preview server...")
    try:
        with client.preview.start(
            file=str(md_path),
            port=7878,
            open_browser=True,
        ) as server:
            print(f"Preview server: {server.url}")
            print(f"File URL:       {server.file_url}")
            print()
            print("Press Enter to stop the preview server...")
            input()
    except Exception as e:
        print(f"Preview server unavailable: {e}")
        print("Run `somark doctor fix` or initialize `vendor/somarkdown-viewer` if preview assets are missing.")
        print("Markdown file has been saved successfully.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
