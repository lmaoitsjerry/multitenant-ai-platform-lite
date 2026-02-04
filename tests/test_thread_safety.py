"""Thread safety tests for DI caching and FAISS singleton."""
import threading
import time
import pytest
from unittest.mock import patch, MagicMock


class TestDICachingThreadSafety:
    """Tests for thread-safe DI caching in routes.py"""

    def test_lru_cache_returns_same_config(self):
        """Verify lru_cache returns same instance for same client_id"""
        from src.api.routes import _get_cached_config

        # Clear cache first
        _get_cached_config.cache_clear()

        with patch('src.api.routes.ClientConfig') as mock_config:
            mock_config.return_value = MagicMock(client_id='test-tenant')

            config1 = _get_cached_config('test-tenant')
            config2 = _get_cached_config('test-tenant')

            # Same instance returned
            assert config1 is config2
            # Constructor called only once
            assert mock_config.call_count == 1

    def test_concurrent_config_access(self):
        """Verify no race condition under concurrent access"""
        from src.api.routes import _get_cached_config

        _get_cached_config.cache_clear()

        results = []
        errors = []

        with patch('src.api.routes.ClientConfig') as mock_config:
            mock_config.return_value = MagicMock(client_id='concurrent-tenant')

            def get_config():
                try:
                    config = _get_cached_config('concurrent-tenant')
                    results.append(config)
                except Exception as e:
                    errors.append(e)

            # Launch 20 concurrent threads
            threads = [threading.Thread(target=get_config) for _ in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            assert len(errors) == 0, f"Errors occurred: {errors}"
            assert len(results) == 20
            # All results should be the same instance
            assert all(r is results[0] for r in results)


class TestFAISSSingletonThreadSafety:
    """Tests for thread-safe FAISS singleton"""

    def test_singleton_returns_same_instance(self):
        """Verify singleton returns same instance"""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton for test
        FAISSHelpdeskService._instance = None

        service1 = FAISSHelpdeskService()
        service2 = FAISSHelpdeskService()

        assert service1 is service2

    def test_concurrent_singleton_creation(self):
        """Verify only one instance created under concurrent access"""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Reset singleton for test
        FAISSHelpdeskService._instance = None

        instances = []
        errors = []

        def create_instance():
            try:
                instance = FAISSHelpdeskService()
                instances.append(instance)
            except Exception as e:
                errors.append(e)

        # Launch 20 concurrent threads
        threads = [threading.Thread(target=create_instance) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(instances) == 20
        # All instances should be the same object
        assert all(i is instances[0] for i in instances)

    def test_double_check_locking_exists(self):
        """Verify the class has proper locking mechanism"""
        from src.services.faiss_helpdesk_service import FAISSHelpdeskService

        # Verify _lock exists and is a Lock
        assert hasattr(FAISSHelpdeskService, '_lock')
        assert isinstance(FAISSHelpdeskService._lock, type(threading.Lock()))


class TestCacheThreadSafety:
    """Tests for LRU cache thread safety."""

    def test_lru_cache_is_thread_safe(self):
        """LRU cache should handle concurrent access safely."""
        from functools import lru_cache

        call_count = 0

        @lru_cache(maxsize=128)
        def cached_func(key):
            nonlocal call_count
            call_count += 1
            time.sleep(0.01)  # Simulate slow operation
            return f"value_{key}"

        results = []
        errors = []

        def access_cache(key):
            try:
                result = cached_func(key)
                results.append(result)
            except Exception as e:
                errors.append(e)

        # Launch concurrent threads accessing same key
        threads = [threading.Thread(target=access_cache, args=("same_key",)) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) == 10
        # All results should be the same
        assert all(r == "value_same_key" for r in results)
        # Should have been called only once (or a few times due to race)
        assert call_count <= 3  # Allow some tolerance for race conditions

    def test_different_keys_cached_independently(self):
        """Different cache keys should be independent."""
        from src.api.routes import _get_cached_config

        _get_cached_config.cache_clear()

        with patch('src.api.routes.ClientConfig') as mock_config:
            configs = {}

            def make_config(client_id):
                configs[client_id] = MagicMock(client_id=client_id)
                return configs[client_id]

            mock_config.side_effect = make_config

            # Access different keys
            config_a = _get_cached_config('tenant-a')
            config_b = _get_cached_config('tenant-b')

            assert config_a.client_id == 'tenant-a'
            assert config_b.client_id == 'tenant-b'
            assert config_a is not config_b


class TestLockContention:
    """Tests for lock contention scenarios."""

    def test_lock_acquisition_timeout(self):
        """Test behavior when lock is held for extended time."""
        lock = threading.Lock()
        results = []

        def worker(wait_time):
            with lock:
                time.sleep(wait_time)
                results.append(threading.current_thread().name)

        t1 = threading.Thread(target=worker, args=(0.1,), name="worker1")
        t2 = threading.Thread(target=worker, args=(0.01,), name="worker2")

        t1.start()
        time.sleep(0.01)  # Let t1 acquire lock first
        t2.start()

        t1.join()
        t2.join()

        # Both should complete, t1 first
        assert results[0] == "worker1"
        assert results[1] == "worker2"

    def test_no_deadlock_with_nested_locks(self):
        """Verify no deadlock with ordered lock acquisition."""
        lock1 = threading.Lock()
        lock2 = threading.Lock()
        completed = []

        def worker1():
            with lock1:
                time.sleep(0.01)
                with lock2:
                    completed.append("w1")

        def worker2():
            with lock1:  # Same order as worker1
                time.sleep(0.01)
                with lock2:
                    completed.append("w2")

        t1 = threading.Thread(target=worker1)
        t2 = threading.Thread(target=worker2)

        t1.start()
        t2.start()

        t1.join(timeout=2)
        t2.join(timeout=2)

        # Both should complete
        assert len(completed) == 2


class TestRaceConditionProtection:
    """Tests for race condition protection."""

    def test_check_then_act_race(self):
        """Test protection against check-then-act race conditions."""
        cache = {}
        lock = threading.Lock()
        creation_count = 0

        def get_or_create(key):
            nonlocal creation_count
            # Without lock, this would have race conditions
            with lock:
                if key not in cache:
                    time.sleep(0.01)  # Simulate slow creation
                    creation_count += 1
                    cache[key] = f"value_{creation_count}"
                return cache[key]

        results = []
        threads = [threading.Thread(target=lambda: results.append(get_or_create("key"))) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should create only once
        assert creation_count == 1
        # All results should be the same
        assert all(r == "value_1" for r in results)


class TestConcurrentModification:
    """Tests for concurrent modification scenarios."""

    def test_dict_concurrent_access(self):
        """Test safe concurrent dict access pattern."""
        from collections import defaultdict

        data = defaultdict(list)
        lock = threading.Lock()

        def append_item(key, value):
            with lock:
                data[key].append(value)

        threads = []
        for i in range(100):
            t = threading.Thread(target=append_item, args=("key", i))
            threads.append(t)

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(data["key"]) == 100

    def test_list_append_thread_safety(self):
        """Test list append is thread-safe for simple cases."""
        results = []

        def append_value(value):
            results.append(value)

        threads = [threading.Thread(target=append_value, args=(i,)) for i in range(50)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 50
        assert sorted(results) == list(range(50))
