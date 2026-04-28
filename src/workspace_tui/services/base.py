import threading
import time
from collections.abc import Callable
from typing import TypeVar

from loguru import logger

from workspace_tui.cache.cache_manager import CacheManager
from workspace_tui.services.errors import (
    AuthenticationError,
    ConnectionError,
    PermissionError,
    RateLimitError,
    ServiceError,
)

T = TypeVar("T")

MAX_RETRIES = 3
BACKOFF_BASE = 1.0
BACKOFF_MAX = 30.0


class BaseService:
    """Base class for all API service wrappers.

    Provides retry with exponential backoff, error categorization, and caching.
    """

    def __init__(self, cache: CacheManager) -> None:
        self._cache = cache
        self._api_lock = threading.Lock()

    def _retry(
        self,
        operation: Callable[[], T],
        *,
        max_retries: int = MAX_RETRIES,
        on_auth_error: Callable[[], None] | None = None,
    ) -> T:
        """Execute operation with retry and exponential backoff.

        Parameters
        ----------
        operation : Callable
            The API call to execute.
        max_retries : int
            Maximum number of retry attempts.
        on_auth_error : Callable | None
            Callback to refresh credentials on 401.

        Returns
        -------
        T
            The result of the operation.
        """
        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                with self._api_lock:
                    return operation()
            except Exception as exc:
                last_exception = exc
                error = self._categorize_error(exc)

                if isinstance(error, AuthenticationError) and on_auth_error and attempt == 0:
                    logger.info("Auth error, attempting credential refresh")
                    on_auth_error()
                    continue

                if isinstance(error, PermissionError | AuthenticationError):
                    raise error from exc

                is_retryable = isinstance(error, RateLimitError | ConnectionError) or (
                    isinstance(error, ServiceError) and error.code == "SERVER_ERROR"
                )
                if is_retryable and attempt < max_retries:
                    delay = min(BACKOFF_BASE * (2**attempt), BACKOFF_MAX)
                    logger.warning(
                        "Retry {}/{} after {:.1f}s: {}",
                        attempt + 1,
                        max_retries,
                        delay,
                        error.message,
                    )
                    time.sleep(delay)
                    continue

                raise error from exc

        raise ServiceError(f"Max retries exceeded: {last_exception}")

    def _categorize_error(self, exc: Exception) -> ServiceError:
        """Categorize an exception into a ServiceError subclass."""
        if isinstance(exc, ServiceError):
            return exc

        exc_str = str(exc).lower()
        exc_type = type(exc).__name__

        # Google API HttpError
        if exc_type == "HttpError" and hasattr(exc, "resp"):
            status = getattr(exc, "resp", {}).get("status", "0")
            status_code = int(status)
            return self._categorize_http_status(status_code, str(exc))

        # requests HTTPError
        if hasattr(exc, "response") and hasattr(exc.response, "status_code"):
            return self._categorize_http_status(exc.response.status_code, str(exc))

        if "connection" in exc_str or "timeout" in exc_str:
            return ConnectionError(service=self.__class__.__name__)

        return ServiceError(message=str(exc))

    def _categorize_http_status(self, status_code: int, message: str) -> ServiceError:
        if status_code == 401:
            return AuthenticationError()
        if status_code == 403:
            return PermissionError()
        if status_code == 404:
            return ServiceError(message=message, code="NOT_FOUND")
        if status_code == 429:
            return RateLimitError()
        if status_code >= 500:
            return ServiceError(message=message, code="SERVER_ERROR")
        return ServiceError(message=message)

    def _cached(self, key: str, ttl: int, fetch: Callable[[], T]) -> T:
        """Get from cache or fetch and cache the result."""
        cached = self._cache.get(key)
        if cached is not None:
            return cached  # type: ignore[return-value]
        result = fetch()
        self._cache.set(key=key, value=result, ttl=ttl)
        return result
