"""
test_gateway_failover.py — Unit tests for instant gateway failover on fatal HTTP client errors.
"""

import time
import urllib.error
import pytest

from src.gateway.facade import retry_with_backoff, is_fatal_http_error


def test_is_fatal_http_error():
    # 404 Not Found, 401 Unauthorized, 403 Forbidden, 400 Bad Request should be fatal
    err_404 = urllib.error.HTTPError("http://api.example.com", 404, "Not Found", {}, None)
    err_401 = urllib.error.HTTPError("http://api.example.com", 401, "Unauthorized", {}, None)
    err_403 = urllib.error.HTTPError("http://api.example.com", 403, "Forbidden", {}, None)
    err_429 = urllib.error.HTTPError("http://api.example.com", 429, "Too Many Requests", {}, None)
    err_500 = urllib.error.HTTPError("http://api.example.com", 500, "Internal Server Error", {}, None)
    err_str_404 = RuntimeError("HTTP Error 404: Not Found")

    assert is_fatal_http_error(err_404) is True
    assert is_fatal_http_error(err_401) is True
    assert is_fatal_http_error(err_403) is True
    assert is_fatal_http_error(err_str_404) is True
    assert is_fatal_http_error(err_429) is False  # 429 is rate limit (handled separately)
    assert is_fatal_http_error(err_500) is False  # 500 is transient server error


def test_retry_with_backoff_bypasses_fatal_http_error():
    call_count = 0

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    def failing_call():
        nonlocal call_count
        call_count += 1
        raise urllib.error.HTTPError("http://api.example.com", 404, "Not Found", {}, None)

    start_time = time.time()
    with pytest.raises(urllib.error.HTTPError):
        failing_call()
    elapsed = time.time() - start_time

    # Should have failed on attempt 1 without sleeping for 1s+2s+4s (7 seconds)
    assert call_count == 1
    assert elapsed < 0.5, f"Fatal error should fail immediately without backoff; took {elapsed:.2f}s"
