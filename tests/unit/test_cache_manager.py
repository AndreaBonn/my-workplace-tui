import tempfile

from workspace_tui.cache.cache_manager import CacheManager


class TestCacheManager:
    def test_get_returns_none_when_disabled(self):
        cache = CacheManager(enabled=False)
        assert cache.get("key") is None

    def test_set_and_get(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(enabled=True, base_dir=tmpdir)
            cache.set(key="test_key", value={"data": 42}, ttl=300)
            result = cache.get("test_key")
            assert result == {"data": 42}
            cache.close()

    def test_get_miss(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(enabled=True, base_dir=tmpdir)
            assert cache.get("nonexistent") is None
            cache.close()

    def test_invalidate(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(enabled=True, base_dir=tmpdir)
            cache.set(key="key1", value="value1", ttl=300)
            cache.invalidate("key1")
            assert cache.get("key1") is None
            cache.close()

    def test_invalidate_prefix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(enabled=True, base_dir=tmpdir)
            cache.set(key="gmail:inbox", value="data1", ttl=300)
            cache.set(key="gmail:sent", value="data2", ttl=300)
            cache.set(key="jira:issues", value="data3", ttl=300)
            cache.invalidate_prefix("gmail:")
            assert cache.get("gmail:inbox") is None
            assert cache.get("gmail:sent") is None
            assert cache.get("jira:issues") == "data3"
            cache.close()

    def test_clear(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = CacheManager(enabled=True, base_dir=tmpdir)
            cache.set(key="k1", value="v1", ttl=300)
            cache.set(key="k2", value="v2", ttl=300)
            cache.clear()
            assert cache.get("k1") is None
            assert cache.get("k2") is None
            cache.close()

    def test_set_noop_when_disabled(self):
        cache = CacheManager(enabled=False)
        cache.set(key="key", value="value", ttl=300)
        assert cache.get("key") is None

    def test_invalidate_noop_when_disabled(self):
        cache = CacheManager(enabled=False)
        cache.invalidate("key")

    def test_clear_noop_when_disabled(self):
        cache = CacheManager(enabled=False)
        cache.clear()
