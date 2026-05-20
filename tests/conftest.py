import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_api_key():
    return "sk-test-key-1234567890"


@pytest.fixture
def base_url():
    return "https://somark.tech/api/v1"


@pytest.fixture
def mock_http(mock_api_key, base_url):
    """Create a mock HttpClient."""
    from somark._http import HttpClient
    client = MagicMock(spec=HttpClient)
    client.api_key = mock_api_key
    client.base_url = base_url
    return client


@pytest.fixture
def parse_response_data():
    return {
        "code": 0,
        "message": "任务成功",
        "data": {
            "task_id": "abc123",
            "error": None,
            "metadata": {"page_num": 5, "file_type": ".pdf"},
            "result": {
                "file_name": "test.pdf",
                "imgs": ["http://example.com/img1.png"],
                "outputs": {
                    "markdown": "# Hello World\n\nThis is a test.",
                    "json": {"pages": []},
                    "zip": None,
                },
            },
        },
    }


@pytest.fixture
def usage_response_data():
    return {
        "code": 0,
        "message": "",
        "data": {
            "remaining_paid_pages": 104410,
            "remaining_free_pages_today": 295,
            "remaining_free_pages_this_month": 578,
            "dashboard_url": "https://somark.tech/workbench",
        },
    }
