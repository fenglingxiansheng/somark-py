class SoMarkError(Exception):
    """Base exception for all SoMark errors."""
    def __init__(self, message: str = "", code: int = -1):
        self.code = code
        super().__init__(message)

class AuthenticationError(SoMarkError):
    """Raised when api_key is missing or invalid (code 1107)."""

class InsufficientBalanceError(SoMarkError):
    """Raised when balance is insufficient (code 1108/1123)."""

class RateLimitError(SoMarkError):
    """Raised when rate limit is exceeded (code 1101/1124)."""

class UnsupportedFileError(SoMarkError):
    """Raised for unsupported file types (code 1104)."""

class FileTooLargeError(SoMarkError):
    """Raised when file is too large (code 1118/1132)."""

class ParseTimeoutError(SoMarkError):
    """Raised when parsing times out (code 1102)."""

class ParseFailedError(SoMarkError):
    """Raised when parsing fails (code 1137)."""

class InvalidParamError(SoMarkError):
    """Raised for invalid parameters (code 1133)."""

class APIError(SoMarkError):
    """Raised for other non-zero API codes."""

class ConnectionError(SoMarkError):
    """Raised when network connection fails."""

class TimeoutError(SoMarkError):
    """Raised when HTTP request times out."""


# Map API code → exception class
CODE_TO_EXCEPTION = {
    1101: RateLimitError,
    1102: ParseTimeoutError,
    1104: UnsupportedFileError,
    1105: InvalidParamError,
    1106: InvalidParamError,
    1107: AuthenticationError,
    1108: InsufficientBalanceError,
    1111: APIError,
    1118: FileTooLargeError,
    1120: APIError,
    1123: InsufficientBalanceError,
    1124: RateLimitError,
    1132: FileTooLargeError,
    1133: InvalidParamError,
    1137: ParseFailedError,
    1138: APIError,
}


def raise_for_code(code: int, message: str = "") -> None:
    """Raise the appropriate exception for a given API error code."""
    exc_class = CODE_TO_EXCEPTION.get(code, APIError)
    raise exc_class(message or f"API error (code={code})", code=code)
