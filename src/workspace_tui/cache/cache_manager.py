from pathlib import Path

from diskcache import Cache
from loguru import logger


class CacheManager:
    """Wrapper around diskcache with per-key TTL support."""

    def __init__(self, *, enabled: bool = True, base_dir: str | None = None) -> None:
        self._enabled = enabled
        if not enabled:
            self._cache = None
            return

        cache_dir = base_dir or str(Path.home() / ".local" / "share" / "workspace-tui" / "cache")
        self._cache = Cache(directory=cache_dir)
        logger.debug("Cache initialized at {}", cache_dir)

    def get(self, key: str) -> object | None:
        if not self._enabled or self._cache is None:
            return None
        value = self._cache.get(key)
        if value is not None:
            logger.debug("Cache hit: {}", key)
        return value

    def set(self, key: str, value: object, ttl: int) -> None:
        if not self._enabled or self._cache is None:
            return
        self._cache.set(key=key, value=value, expire=ttl)
        logger.debug("Cache set: {} (ttl={}s)", key, ttl)

    def invalidate(self, key: str) -> None:
        if not self._enabled or self._cache is None:
            return
        self._cache.delete(key)
        logger.debug("Cache invalidated: {}", key)

    def invalidate_prefix(self, prefix: str) -> None:
        """Invalidate all keys starting with the given prefix."""
        if not self._enabled or self._cache is None:
            return
        keys_to_delete = [k for k in self._cache if isinstance(k, str) and k.startswith(prefix)]
        for key in keys_to_delete:
            self._cache.delete(key)
        if keys_to_delete:
            logger.debug("Cache invalidated {} keys with prefix '{}'", len(keys_to_delete), prefix)

    def clear(self) -> None:
        if not self._enabled or self._cache is None:
            return
        self._cache.clear()
        logger.debug("Cache cleared")

    def close(self) -> None:
        if self._cache is not None:
            self._cache.close()
