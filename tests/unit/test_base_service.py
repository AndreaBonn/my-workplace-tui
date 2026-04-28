import tempfile

import pytest

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.base import BaseService
from workspace_tui.services.errors import (
    AuthenticationError,
    ConnectionError,
    PermissionError,
    RateLimitError,
    ServiceError,
)


@pytest.fixture
def cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        cm = CacheManager(enabled=True, base_dir=tmpdir)
        yield cm
        cm.close()


@pytest.fixture
def service(cache):
    return BaseService(cache=cache)


class TestRetry:
    def test_success_on_first_try(self, service):
        result = service._retry(lambda: "ok")
        assert result == "ok"

    def test_retries_on_connection_error(self, service):
        call_count = 0

        def failing_then_ok():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise OSError("Connection refused")
            return "recovered"

        result = service._retry(failing_then_ok, max_retries=3)
        assert result == "recovered"
        assert call_count == 3

    def test_raises_permission_error_immediately(self, service):
        def perm_error():
            raise PermissionError("No access")

        with pytest.raises(PermissionError):
            service._retry(perm_error)

    def test_calls_auth_refresh_on_401(self, service):
        refresh_called = False
        call_count = 0

        def auth_error_then_ok():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise AuthenticationError()
            return "ok"

        def refresh():
            nonlocal refresh_called
            refresh_called = True

        result = service._retry(auth_error_then_ok, on_auth_error=refresh)
        assert result == "ok"
        assert refresh_called

    def test_max_retries_exceeded(self, service):
        def always_fails():
            raise OSError("Connection refused")

        with pytest.raises(ServiceError):
            service._retry(always_fails, max_retries=2)


class TestCategorizeError:
    def test_service_error_passthrough(self, service):
        err = ServiceError("test")
        assert service._categorize_error(err) is err

    def test_connection_error_detected(self, service):
        err = OSError("Connection refused")
        result = service._categorize_error(err)
        assert isinstance(result, ConnectionError)

    def test_timeout_error_detected(self, service):
        err = TimeoutError("Request timeout")
        result = service._categorize_error(err)
        assert isinstance(result, ConnectionError)


class TestCategorizeHttpStatus:
    def test_401(self, service):
        assert isinstance(service._categorize_http_status(401, ""), AuthenticationError)

    def test_403(self, service):
        assert isinstance(service._categorize_http_status(403, ""), PermissionError)

    def test_429(self, service):
        assert isinstance(service._categorize_http_status(429, ""), RateLimitError)

    def test_500(self, service):
        result = service._categorize_http_status(500, "server error")
        assert isinstance(result, ServiceError)
        assert result.code == "SERVER_ERROR"

    def test_404(self, service):
        result = service._categorize_http_status(404, "not found")
        assert result.code == "NOT_FOUND"


class TestCached:
    def test_fetches_and_caches(self, service):
        call_count = 0

        def fetch():
            nonlocal call_count
            call_count += 1
            return {"data": 42}

        result1 = service._cached("test_key", ttl=300, fetch=fetch)
        result2 = service._cached("test_key", ttl=300, fetch=fetch)
        assert result1 == {"data": 42}
        assert result2 == {"data": 42}
        assert call_count == 1
