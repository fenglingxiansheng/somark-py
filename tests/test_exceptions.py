import pytest
from somark._exceptions import (
    AuthenticationError, RateLimitError, FileTooLargeError,
    APIError, raise_for_code
)


@pytest.mark.parametrize(
    ("code", "exception_type"),
    [
        (1107, AuthenticationError),
        (1101, RateLimitError),
        (1124, RateLimitError),
        (1118, FileTooLargeError),
        (1132, FileTooLargeError),
    ],
)
def test_raise_for_code_maps_known_service_codes(code, exception_type):
    with pytest.raises(exception_type):
        raise_for_code(code, "service message")


def test_raise_for_code_unknown():
    with pytest.raises(APIError):
        raise_for_code(9999, "unknown")


def test_exception_has_code():
    try:
        raise_for_code(1107, "bad key")
    except AuthenticationError as e:
        assert e.code == 1107
        assert "bad key" in str(e)
