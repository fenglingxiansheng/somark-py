import pytest
from unittest.mock import MagicMock
from somark.resources.usage import UsageClient
from somark._models import Usage
from somark._exceptions import AuthenticationError
from somark import SoMarkWarning


def test_usage_requires_api_key():
    http = MagicMock()
    http.api_key = None
    resource = UsageClient(http)
    with pytest.raises(AuthenticationError):
        resource.get()


def test_usage_returns_object(mock_http, usage_response_data):
    mock_http.post.return_value = usage_response_data
    resource = UsageClient(mock_http)
    usage = resource.get()
    assert isinstance(usage, Usage)
    assert usage.remaining_paid_pages == 104410
    assert usage.remaining_free_pages_today == 295
    assert usage.remaining_free_pages_this_month == 578


def test_usage_resource_emits_api_warnings(mock_http, usage_response_data):
    mock_http.post.return_value = {**usage_response_data, "warnings": ["usage warning"]}
    resource = UsageClient(mock_http)
    with pytest.warns(SoMarkWarning, match="usage warning"):
        usage = resource.get()
    assert usage.warnings == ["usage warning"]
