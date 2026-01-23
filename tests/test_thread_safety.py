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
