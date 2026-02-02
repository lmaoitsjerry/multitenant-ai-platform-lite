"""
Travel Platform RAG Client

Connects to the centralized Travel Platform RAG API for knowledge base queries.
Replaces local FAISS with the Travel Platform's RAG service.

Configuration via environment variables:
- TRAVEL_PLATFORM_URL: Base URL (default: http://localhost:8000)
- TRAVEL_PLATFORM_API_KEY: API key for authentication
- TRAVEL_PLATFORM_TENANT: Tenant slug (default: itc)
- TRAVEL_PLATFORM_TIMEOUT: Request timeout in seconds (default: 30)
"""

import os
import logging
from typing import Optional, Dict, Any, List

import requests

from src.utils.circuit_breaker import rag_circuit
from src.utils.retry_utils import retry_on_network_error

logger = logging.getLogger(__name__)


class TravelPlatformRAGClient:
    """
    Client for the Travel Platform RAG API.

    Provides knowledge base search via the centralized RAG service.
    """

    _instance = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.base_url = os.getenv("TRAVEL_PLATFORM_URL", "http://localhost:8000")
        self.api_key = os.getenv("TRAVEL_PLATFORM_API_KEY", "")
        self.tenant_slug = os.getenv("TRAVEL_PLATFORM_TENANT", "itc")
        self.timeout = int(os.getenv("TRAVEL_PLATFORM_TIMEOUT", "30"))

        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}" if self.api_key else "",
        })

        self._initialized = True
        self._last_error = None

        logger.info(
            f"Travel Platform RAG client initialized: "
            f"url={self.base_url}, tenant={self.tenant_slug}, timeout={self.timeout}s"
        )

    def is_available(self) -> bool:
        """Check if Travel Platform RAG API is accessible."""
        try:
            # Health endpoint doesn't require auth
            # Use configured timeout to handle Cloud Run cold starts
            response = requests.get(
                f"{self.base_url}/api/v1/rag/health",
                timeout=self.timeout
            )
            if response.status_code == 200:
                data = response.json()
                status = data.get("status", "unknown")
                if status in ("healthy", "degraded"):
                    logger.debug(
                        f"Travel Platform RAG available: status={status}, "
                        f"db={data.get('database')}, warmed_up={data.get('warmed_up')}"
                    )
                    return True
            logger.warning(f"Travel Platform RAG health check failed: {response.status_code}")
            return False
        except Exception as e:
            logger.warning(f"Travel Platform RAG not available: {e}")
            return False

    def search(
        self,
        query: str,
        top_k: int = 5,
        include_shared: bool = True
    ) -> Dict[str, Any]:
        """
        Search the knowledge base via Travel Platform RAG.

        Args:
            query: Search query
            top_k: Number of results (default 5)
            include_shared: Include shared knowledge base documents (default True)

        Returns:
            {
                "success": bool,
                "answer": str,
                "citations": List[Dict],
                "confidence": float,
                "latency_ms": int,
                "query_id": str
            }
        """
        if not rag_circuit.can_execute():
            logger.warning("Travel Platform RAG circuit breaker OPEN — skipping search")
            return self._error_response("Circuit breaker open")

        url = f"{self.base_url}/api/v1/rag/search"

        payload = {
            "query": query,
            "top_k": top_k,
            "include_shared": include_shared
        }

        try:
            response = self._post_with_retry(url, payload)
            response.raise_for_status()

            data = response.json()

            rag_circuit.record_success()

            logger.info(
                f"Travel Platform RAG search: query='{query[:50]}...', "
                f"confidence={data.get('confidence', 0):.2f}, "
                f"citations={len(data.get('citations', []))}, "
                f"latency={data.get('latency_ms', 0)}ms"
            )

            return {
                "success": True,
                "answer": data.get("answer", ""),
                "citations": data.get("citations", []),
                "confidence": data.get("confidence", 0.0),
                "latency_ms": data.get("latency_ms", 0),
                "query_id": data.get("query_id", "")
            }

        except requests.exceptions.Timeout:
            self._last_error = f"Request timed out after {self.timeout}s"
            logger.error(f"Travel Platform RAG timeout: {self._last_error}")
            rag_circuit.record_failure()
            return self._error_response(self._last_error)

        except requests.exceptions.ConnectionError as e:
            self._last_error = f"Connection failed: {e}"
            logger.error(f"Travel Platform RAG connection error: {self._last_error}")
            rag_circuit.record_failure()
            return self._error_response(self._last_error)

        except requests.exceptions.HTTPError as e:
            self._last_error = f"HTTP {e.response.status_code}: {e.response.text[:200]}"
            logger.error(f"Travel Platform RAG HTTP error: {self._last_error}")
            rag_circuit.record_failure()
            return self._error_response(self._last_error)

        except Exception as e:
            self._last_error = str(e)
            logger.error(f"Travel Platform RAG error: {self._last_error}")
            rag_circuit.record_failure()
            return self._error_response(self._last_error)

    @retry_on_network_error(max_attempts=3, min_wait=2, max_wait=10)
    def _post_with_retry(self, url: str, payload: dict):
        """POST with retry on transient network errors."""
        return self.session.post(url, json=payload, timeout=self.timeout)

    def _error_response(self, error: str) -> Dict[str, Any]:
        """Return error response structure."""
        return {
            "success": False,
            "answer": "",
            "citations": [],
            "confidence": 0.0,
            "latency_ms": 0,
            "error": error
        }

    def get_status(self) -> Dict[str, Any]:
        """Get client status."""
        available = self.is_available()
        return {
            "initialized": self._initialized,
            "available": available,
            "base_url": self.base_url,
            "tenant": self.tenant_slug,
            "timeout": self.timeout,
            "last_error": self._last_error
        }


# Singleton accessor
_client: Optional[TravelPlatformRAGClient] = None


def get_travel_platform_rag_client() -> TravelPlatformRAGClient:
    """Get the singleton Travel Platform RAG client."""
    global _client
    if _client is None:
        _client = TravelPlatformRAGClient()
    return _client


def reset_travel_platform_rag_client():
    """Reset the singleton client (for testing)."""
    global _client
    TravelPlatformRAGClient._instance = None
    _client = None
