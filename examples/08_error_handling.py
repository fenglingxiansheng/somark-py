"""
08_error_handling.py — Comprehensive error handling

Demonstrates catching specific error types from the somark error hierarchy.
Parses a Chinese financial report image to show real API interaction,
then illustrates how each error type would be handled.

Run:
    python examples/08_error_handling.py

Requires: SOMARK_API_KEY env var (or ~/.somark/config.toml)
"""

import sys
from pathlib import Path
from typing import Optional

from somark import (
    SoMark,
    SoMarkError,
    AuthenticationError,
    InsufficientBalanceError,
    RateLimitError,
    UnsupportedFileError,
    FileTooLargeError,
    ParseTimeoutError,
    ParseFailedError,
    InvalidParamError,
    APIError,
    ConnectionError,
    TimeoutError,
)
from somark._models import ParseResponse

DATA_DIR = Path(__file__).parent / "data"
IMAGE_FILE = DATA_DIR / "研报1.png"


def parse_with_error_handling(client: SoMark, file: str) -> Optional[ParseResponse]:
    try:
        response = client.parser.parse(
            file=file,
            formats=["md"],
        )

        print(f"Success! Pages: {response.pages}")
        if response.md:
            print("--- Markdown preview (first 300 chars) ---")
            print(response.md[:300])
            print("...")
        return response

    except AuthenticationError as e:
        print(f"[AuthenticationError] Invalid or missing API key.")
        print( "  Set SOMARK_API_KEY env var or run: somark login")

    except InsufficientBalanceError as e:
        print(f"[InsufficientBalanceError] Account has insufficient page balance.")
        print( "  Visit https://somark.tech/workbench to top up.")

    except RateLimitError as e:
        print(f"[RateLimitError] Too many requests. Slow down and retry.")

    except UnsupportedFileError as e:
        print(f"[UnsupportedFileError] File format not supported by the API.")

    except FileTooLargeError as e:
        print(f"[FileTooLargeError] File exceeds the maximum allowed size.")

    except ParseTimeoutError as e:
        print(f"[ParseTimeoutError] The server timed out processing this file.")

    except ParseFailedError as e:
        print(f"[ParseFailedError] The server failed to parse this file. Code: {e.code}")

    except InvalidParamError as e:
        print(f"[InvalidParamError] One or more request parameters are invalid.")

    except APIError as e:
        print(f"[APIError] Unexpected API error. Code: {e.code}")

    except ConnectionError as e:
        print(f"[ConnectionError] Could not reach the SoMark API. Check your network.")

    except TimeoutError as e:
        print(f"[TimeoutError] Request timed out. Try increasing the timeout.")

    except SoMarkError as e:
        print(f"[SoMarkError] code={e.code}: {e}")

    return None


def main() -> None:
    print("=== Example 1: Parse Chinese financial report image ===")
    print(f"File: {IMAGE_FILE}")
    print()

    client = SoMark()
    parse_with_error_handling(client, str(IMAGE_FILE))

    print()
    print("=== Example 2: Simulate AuthenticationError (bad key) ===")
    bad_client = SoMark(api_key="invalid-key-for-demo")
    parse_with_error_handling(bad_client, str(IMAGE_FILE))

    print()
    print("Done.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
