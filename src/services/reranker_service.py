"""
Re-Ranker Service - Cross-Encoder for Better Relevance

Uses a cross-encoder model to re-rank search results for improved relevance.
Cross-encoders are more accurate than bi-encoders for ranking because they
process the query and document together.

Research shows re-ranking can improve retrieval quality by 15-48%.
"""

import logging
from typing import List, Dict, Any, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


class ReRankerService:
    """
    Re-rank search results using a cross-encoder model.

    Uses the ms-marco-MiniLM-L-6-v2 model which is fast and effective
    for passage ranking tasks.
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

        self.model = None
        self._init_error = None
        self._initialized = True

    def _lazy_init(self) -> bool:
        """Lazy initialization of the cross-encoder model"""
        if self.model is not None:
            return True

        if self._init_error:
            return False

        try:
            from sentence_transformers import CrossEncoder

            logger.info("Loading cross-encoder model for re-ranking...")

            # ms-marco-MiniLM-L-6-v2 is optimized for passage ranking
            # It's lightweight (~80MB) and fast (~20ms per batch)
            self.model = CrossEncoder(
                'cross-encoder/ms-marco-MiniLM-L-6-v2',
                max_length=512,
                device='cpu'
            )

            # Warm up the model
            _ = self.model.predict([("test query", "test document")])

            logger.info("Cross-encoder model loaded successfully")
            return True

        except ImportError as e:
            logger.warning(f"sentence-transformers not available for re-ranking: {e}")
            self._init_error = "sentence-transformers not installed"
            return False
        except Exception as e:
            logger.error(f"Failed to initialize re-ranker: {e}")
            self._init_error = str(e)
            return False

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5,
        content_key: str = 'content'
    ) -> List[Dict[str, Any]]:
        """
        Re-rank documents using cross-encoder.

        Args:
            query: User's question
            documents: List of dicts with document content
            top_k: Number of top results to return
            content_key: Key to access document content

        Returns:
            Re-ranked documents with added 'rerank_score'
        """
        if not documents:
            return []

        # If model not available, return original order
        if not self._lazy_init():
            logger.debug("Re-ranker not available, returning original order")
            return documents[:top_k]

        try:
            # Create query-document pairs
            pairs = []
            for doc in documents:
                content = doc.get(content_key, '')
                if isinstance(content, str):
                    # Truncate long content to stay within model limits
                    content = content[:1000] if len(content) > 1000 else content
                    pairs.append((query, content))
                else:
                    pairs.append((query, str(content)[:1000]))

            # Get cross-encoder scores
            scores = self.model.predict(pairs)

            # Add scores to documents
            for doc, score in zip(documents, scores):
                doc['rerank_score'] = float(score)

            # Sort by rerank score (higher is better)
            reranked = sorted(documents, key=lambda x: x.get('rerank_score', 0), reverse=True)

            logger.debug(f"Re-ranked {len(documents)} documents, returning top {top_k}")
            return reranked[:top_k]

        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            return documents[:top_k]

    def is_available(self) -> bool:
        """Check if re-ranker is available"""
        return self._lazy_init()

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        return {
            'initialized': self.model is not None,
            'available': self._init_error is None,
            'error': self._init_error,
            'model': 'cross-encoder/ms-marco-MiniLM-L-6-v2' if self.model else None
        }


# Singleton instance
_reranker = None


def get_reranker() -> ReRankerService:
    """Get singleton re-ranker instance"""
    global _reranker
    if _reranker is None:
        _reranker = ReRankerService()
    return _reranker


def rerank_results(
    query: str,
    documents: List[Dict[str, Any]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """Convenience function for re-ranking results"""
    service = get_reranker()
    return service.rerank(query, documents, top_k)


if __name__ == "__main__":
    # Test the re-ranker
    print("Re-Ranker Service Test")
    print("=" * 60)

    service = ReRankerService()

    # Test documents about hotels
    test_docs = [
        {"content": "The weather in Mauritius is tropical with warm temperatures year-round.", "score": 0.85},
        {"content": "Solana Beach Hotel offers 117 sea-facing rooms with luxury amenities and beach access.", "score": 0.80},
        {"content": "Mauritius is located in the Indian Ocean, east of Madagascar.", "score": 0.82},
        {"content": "Our luxury hotels in Mauritius include 5-star properties with private pools.", "score": 0.78},
        {"content": "The capital of Mauritius is Port Louis, a vibrant city with colonial architecture.", "score": 0.75},
    ]

    query = "What luxury hotels do you have in Mauritius?"
    print(f"\nQuery: {query}")
    print("\nBefore re-ranking:")
    for i, doc in enumerate(test_docs):
        print(f"  {i+1}. (score: {doc['score']:.2f}) {doc['content'][:50]}...")

    reranked = service.rerank(query, test_docs.copy(), top_k=3)

    print("\nAfter re-ranking (top 3):")
    for i, doc in enumerate(reranked):
        rerank_score = doc.get('rerank_score', 'N/A')
        if isinstance(rerank_score, float):
            print(f"  {i+1}. (rerank: {rerank_score:.2f}) {doc['content'][:50]}...")
        else:
            print(f"  {i+1}. {doc['content'][:50]}...")
