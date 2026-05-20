"""
03_async_task.py — Async task submission + polling

Demonstrates parser.create() which submits an async job and returns a Task.
Then calls task.wait() to poll until completion.

Uses AsyncSoMark with asyncio.

Run:
    python examples/03_async_task.py

Requires: SOMARK_API_KEY env var (or ~/.somark/config.toml)
"""

import asyncio
import sys
from pathlib import Path

from somark import AsyncSoMark

DATA_DIR = Path(__file__).parent / "data"
FILE = DATA_DIR / "2010.02399v1.pdf"


async def main() -> None:
    async with AsyncSoMark() as client:
        print(f"Submitting async task for: {FILE}")

        task = await client.parser.create(
            file=str(FILE),
            formats=["md"],
        )

        print(f"Task ID:  {task.id}")
        print(f"Status:   {task.status}")
        print("Polling for completion...\n")

        result = await task.wait(
            poll_interval=3.0,   # seconds between polls
            timeout=120.0,       # max seconds to wait
        )

        print(f"Final status: {task.status}")
        print(f"Pages parsed: {result.pages}")
        print()

        if result.md:
            print("--- Markdown preview (first 400 chars) ---")
            print(result.md[:400])
            print("...\n")

        out_path = Path(__file__).parent / "output_03.md"
        result.save(str(out_path), format="md")
        print(f"Saved to: {out_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
