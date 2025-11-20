"""Tests for HTTP tools connector.

Tests cover:
- Test mode behavior for all HTTP methods
- URL building with base_url
- Retry logic with exponential backoff
- Real mode behavior (mocked)
"""

import pytest
import requests
from unittest.mock import Mock, patch

from apeg_core.connectors.http_tools import HTTPClient


def test_http_client_get_test_mode():
    """Test GET request in test mode returns mock data."""
    client = HTTPClient(base_url="https://api.example.com", test_mode=True)

    result = client.get("/users", params={"limit": 10})

    assert result["test_mode"] is True
    assert result["method"] == "GET"
    assert result["url"] == "https://api.example.com/users"
    assert result["params"] == {"limit": 10}


def test_http_client_post_test_mode():
    """Test POST request in test mode returns mock data."""
    client = HTTPClient(base_url="https://api.example.com", test_mode=True)

    payload = {"name": "Test User", "email": "test@example.com"}
    result = client.post("/users", json=payload)

    assert result["test_mode"] is True
    assert result["method"] == "POST"
    assert result["url"] == "https://api.example.com/users"
    assert result["json"] == payload


def test_http_client_put_test_mode():
    """Test PUT request in test mode returns mock data."""
    client = HTTPClient(base_url="https://api.example.com", test_mode=True)

    payload = {"name": "Updated User"}
    result = client.put("/users/123", json=payload)

    assert result["test_mode"] is True
    assert result["method"] == "PUT"
    assert result["url"] == "https://api.example.com/users/123"
    assert result["json"] == payload


def test_http_client_delete_test_mode():
    """Test DELETE request in test mode returns mock data."""
    client = HTTPClient(base_url="https://api.example.com", test_mode=True)

    result = client.delete("/users/123")

    assert result["test_mode"] is True
    assert result["method"] == "DELETE"
    assert result["url"] == "https://api.example.com/users/123"


def test_http_client_url_building():
    """Test URL building with base_url and relative paths."""
    client = HTTPClient(base_url="https://api.example.com", test_mode=True)

    # Test relative URL
    result1 = client.get("/endpoint")
    assert result1["url"] == "https://api.example.com/endpoint"

    # Test relative URL with leading slash
    result2 = client.get("endpoint")
    assert result2["url"] == "https://api.example.com/endpoint"

    # Test absolute URL (should override base_url)
    result3 = client.get("https://other-api.com/endpoint")
    assert result3["url"] == "https://other-api.com/endpoint"

    # Test without base_url
    client_no_base = HTTPClient(test_mode=True)
    result4 = client_no_base.get("/endpoint")
    assert result4["url"] == "/endpoint"


@patch('apeg_core.connectors.http_tools.requests.request')
def test_http_client_retry_logic_success(mock_request):
    """Test successful request on first attempt."""
    client = HTTPClient(base_url="https://api.example.com", test_mode=False)

    # Mock successful response
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b'{"success": true}'
    mock_response.json.return_value = {"success": True}
    mock_request.return_value = mock_response

    result = client.get("/endpoint")

    assert result == {"success": True}
    assert mock_request.call_count == 1


@patch('apeg_core.connectors.http_tools.requests.request')
@patch('apeg_core.connectors.http_tools.time.sleep')
def test_http_client_retry_logic_with_retries(mock_sleep, mock_request):
    """Test retry logic with exponential backoff."""
    client = HTTPClient(base_url="https://api.example.com", test_mode=False)

    # Mock two failures then success
    mock_response_fail = Mock()
    mock_response_fail.raise_for_status.side_effect = requests.RequestException("Connection error")

    mock_response_success = Mock()
    mock_response_success.status_code = 200
    mock_response_success.content = b'{"success": true}'
    mock_response_success.json.return_value = {"success": True}

    mock_request.side_effect = [
        mock_response_fail,  # First attempt fails
        mock_response_fail,  # Second attempt fails
        mock_response_success  # Third attempt succeeds
    ]

    result = client.get("/endpoint")

    assert result == {"success": True}
    assert mock_request.call_count == 3

    # Verify exponential backoff delays
    assert mock_sleep.call_count == 2
    assert mock_sleep.call_args_list[0][0][0] == 1.0  # First retry: 1s
    assert mock_sleep.call_args_list[1][0][0] == 2.0  # Second retry: 2s


@patch('apeg_core.connectors.http_tools.requests.request')
@patch('apeg_core.connectors.http_tools.time.sleep')
def test_http_client_retry_exhaustion(mock_sleep, mock_request):
    """Test that all retries exhausted raises exception."""
    client = HTTPClient(base_url="https://api.example.com", test_mode=False)

    # Mock all attempts failing
    mock_response_fail = Mock()
    mock_response_fail.raise_for_status.side_effect = requests.RequestException("Connection error")
    mock_request.return_value = mock_response_fail

    with pytest.raises(requests.RequestException):
        client.get("/endpoint")

    # Should attempt 3 times (initial + 2 retries)
    assert mock_request.call_count == 3

    # Should sleep twice (between retries)
    assert mock_sleep.call_count == 2
