"""
FAISS Helpdesk Service - Shared Knowledge Base

Connects to the global FAISS index stored in Google Cloud Storage.
This index contains helpdesk documentation shared across all tenants.

GCS Bucket: zorah-475411-rag-documents
Path: faiss_indexes/
Files:
  - index.faiss (vector index)
  - index.pkl (document metadata/texts)
"""

import os
import pickle
import tempfile
import logging
import threading
from typing import List, Tuple, Optional, Dict, Any
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# GCS Configuration - using the leaner curated index
GCS_BUCKET_NAME = os.getenv("FAISS_BUCKET_NAME", "zorah-475411-rag-documents")
GCS_INDEX_PREFIX = os.getenv("FAISS_INDEX_PREFIX", "faiss_indexes/")
GCS_INDEX_FILE = "index.faiss"
GCS_METADATA_FILE = "index.pkl"

# Local cache directory
CACHE_DIR = Path(tempfile.gettempdir()) / "zorah_faiss_cache"


class FAISSHelpdeskService:
    """
    Service to query the shared FAISS helpdesk index from Google Cloud Storage.

    The index is downloaded once and cached locally for performance.
    Uses the same embeddings model that was used to create the index.
    Thread-safe singleton pattern with double-check locking.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern with double-check locking for thread safety"""
        if cls._instance is None:
            with cls._lock:
                # Double-check inside lock to prevent race condition
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.index = None
        self.docstore = None  # LangChain InMemoryDocstore
        self.index_to_docstore_id = None  # Maps FAISS index -> document ID
        self.embeddings_model = None
        self._initialized = False
        self._init_error = None

        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_gcs_client(self):
        """Get GCS client"""
        try:
            from google.cloud import storage
            return storage.Client()
        except Exception as e:
            logger.error(f"Failed to create GCS client: {e}")
            return None

    def _download_from_gcs(self, blob_name: str, local_path: Path) -> bool:
        """Download a file from GCS if not already cached or if stale"""
        try:
            client = self._get_gcs_client()
            if not client:
                return False

            bucket = client.bucket(GCS_BUCKET_NAME)
            blob = bucket.blob(blob_name)

            # Check if blob exists
            if not blob.exists():
                logger.error(f"Blob {blob_name} not found in bucket {GCS_BUCKET_NAME}")
                return False

            # Check if local file exists and is recent (within 24 hours)
            if local_path.exists():
                import time
                file_age = time.time() - local_path.stat().st_mtime
                if file_age < 86400:  # 24 hours
                    logger.info(f"Using cached {blob_name} (age: {file_age/3600:.1f} hours)")
                    return True

            # Download file
            logger.info(f"Downloading {blob_name} from GCS bucket {GCS_BUCKET_NAME}...")
            blob.download_to_filename(str(local_path))
            logger.info(f"Downloaded {blob_name} ({local_path.stat().st_size / 1024 / 1024:.1f} MB)")
            return True

        except Exception as e:
            logger.error(f"Failed to download {blob_name} from GCS: {e}")
            return False

    def _get_embeddings_model(self):
        """Get the embeddings model - must match what was used to build the index (768 dimensions)"""
        if self.embeddings_model is not None:
            return self.embeddings_model

        # The FAISS index was built with 768-dimensional embeddings
        # Use sentence-transformers all-mpnet-base-v2 which produces 768 dimensions
        # Note: OpenAI embeddings (1536 dim) don't match this index

        # Set HuggingFace environment to reduce memory and network issues
        import os
        os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY', '1')
        os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

        # Try sentence-transformers (use 768-dim model to match index)
        try:
            from sentence_transformers import SentenceTransformer

            class SentenceTransformerWrapper:
                def __init__(self):
                    # Use all-mpnet-base-v2 which produces 768 dimensions
                    # This matches the FAISS index dimension
                    # Use local_files_only=True if already cached to avoid network issues
                    try:
                        self.model = SentenceTransformer(
                            'all-mpnet-base-v2',
                            device='cpu'
                        )
                    except Exception as e:
                        logger.warning(f"Failed to load model normally, trying offline: {e}")
                        self.model = SentenceTransformer(
                            'all-mpnet-base-v2',
                            device='cpu',
                            local_files_only=True
                        )

                def embed_query(self, text: str) -> List[float]:
                    return self.model.encode(text, show_progress_bar=False).tolist()

                def embed_documents(self, texts: List[str]) -> List[List[float]]:
                    return self.model.encode(texts, show_progress_bar=False).tolist()

            self.embeddings_model = SentenceTransformerWrapper()
            logger.info("Using sentence-transformers (all-mpnet-base-v2, 768-dim) for FAISS search")
            return self.embeddings_model
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers: {e}")

        return None

    def initialize(self) -> bool:
        """
        Initialize the service by downloading and loading the FAISS index.

        Returns True if successful, False otherwise.
        """
        if self._initialized:
            return True

        if self._init_error:
            return False

        try:
            logger.info(f"Initializing FAISS Helpdesk Service from {GCS_BUCKET_NAME}/{GCS_INDEX_PREFIX}...")

            # Local file paths
            index_path = CACHE_DIR / GCS_INDEX_FILE
            metadata_path = CACHE_DIR / GCS_METADATA_FILE

            # Download files from GCS (with prefix for subdirectory)
            gcs_index_path = f"{GCS_INDEX_PREFIX}{GCS_INDEX_FILE}"
            gcs_metadata_path = f"{GCS_INDEX_PREFIX}{GCS_METADATA_FILE}"

            if not self._download_from_gcs(gcs_index_path, index_path):
                self._init_error = f"Failed to download FAISS index from {gcs_index_path}"
                return False

            if not self._download_from_gcs(gcs_metadata_path, metadata_path):
                self._init_error = f"Failed to download metadata file from {gcs_metadata_path}"
                return False

            # Load FAISS index
            logger.info("Loading FAISS index...")
            import faiss
            self.index = faiss.read_index(str(index_path))
            logger.info(f"FAISS index loaded: {self.index.ntotal} vectors")

            # Load document metadata
            logger.info("Loading document metadata...")
            with open(metadata_path, 'rb') as f:
                data = pickle.load(f)

            # Handle LangChain FAISS format: tuple of (InMemoryDocstore, index_to_docstore_id)
            if isinstance(data, tuple) and len(data) == 2:
                self.docstore, self.index_to_docstore_id = data
                doc_count = len(self.index_to_docstore_id) if self.index_to_docstore_id else 0
                logger.info(f"Loaded LangChain docstore with {doc_count} document mappings")
            elif isinstance(data, dict):
                # Alternative dict format
                if 'docstore' in data and 'index_to_docstore_id' in data:
                    self.docstore = data['docstore']
                    self.index_to_docstore_id = data['index_to_docstore_id']
                    doc_count = len(self.index_to_docstore_id)
                else:
                    # Simple dict of documents
                    self.index_to_docstore_id = {i: str(i) for i in range(len(data))}
                    self.docstore = data
                    doc_count = len(data)
                logger.info(f"Loaded {doc_count} documents from metadata dict")
            else:
                # Fallback: treat as list
                self.index_to_docstore_id = {i: str(i) for i in range(len(data))}
                self.docstore = data
                doc_count = len(data) if data else 0
                logger.info(f"Loaded {doc_count} documents from metadata list")

            # Initialize embeddings model
            if not self._get_embeddings_model():
                self._init_error = "No embeddings model available"
                return False

            self._initialized = True
            logger.info("FAISS Helpdesk Service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize FAISS service: {e}", exc_info=True)
            self._init_error = str(e)
            return False

    def _get_document(self, faiss_idx: int):
        """
        Retrieve a document by its FAISS index.

        Handles LangChain InMemoryDocstore format where we need to:
        1. Map FAISS index -> document ID via index_to_docstore_id
        2. Look up document in docstore using the document ID
        """
        if faiss_idx == -1:
            return None

        # Get document ID from the mapping
        doc_id = self.index_to_docstore_id.get(faiss_idx)
        if doc_id is None:
            logger.warning(f"No document ID found for FAISS index {faiss_idx}")
            return None

        # Retrieve document from docstore
        if hasattr(self.docstore, 'search'):
            # LangChain InMemoryDocstore
            doc = self.docstore.search(doc_id)
            if doc is None or (isinstance(doc, str) and 'not found' in doc.lower()):
                logger.warning(f"Document {doc_id} not found in docstore")
                return None
            return doc
        elif hasattr(self.docstore, '_dict'):
            # Direct access to internal dict
            return self.docstore._dict.get(doc_id)
        elif isinstance(self.docstore, dict):
            return self.docstore.get(doc_id)
        elif isinstance(self.docstore, list):
            try:
                return self.docstore[int(doc_id)]
            except (ValueError, IndexError):
                return None

        return None

    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search the FAISS index for relevant documents.

        Args:
            query: The search query
            top_k: Number of results to return

        Returns:
            List of dicts with 'content', 'score', and optional metadata
        """
        if not self._initialized and not self.initialize():
            logger.warning("FAISS service not initialized, returning empty results")
            return []

        try:
            import numpy as np

            # Generate embedding for the query
            query_embedding = self.embeddings_model.embed_query(query)
            query_vector = np.array([query_embedding]).astype('float32')

            # Search the index
            distances, indices = self.index.search(query_vector, top_k)

            # Build results
            results = []
            for i, idx in enumerate(indices[0]):
                if idx == -1:
                    continue

                doc = self._get_document(idx)
                if doc is None:
                    continue

                # Handle different document formats
                if isinstance(doc, dict):
                    content = doc.get('text', doc.get('content', doc.get('page_content', str(doc))))
                    source = doc.get('source', doc.get('metadata', {}).get('source', 'Knowledge Base'))
                elif hasattr(doc, 'page_content'):
                    # LangChain Document object
                    content = doc.page_content
                    source = getattr(doc, 'metadata', {}).get('source', 'Knowledge Base')
                else:
                    content = str(doc)
                    source = 'Knowledge Base'

                # Convert L2 distance to similarity score
                distance = float(distances[0][i])
                score = 1 / (1 + distance)

                results.append({
                    'content': content,
                    'source': source,
                    'score': round(score, 3),
                    'index': int(idx)
                })

            logger.info(f"FAISS search for '{query[:50]}...' returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"FAISS search failed: {e}", exc_info=True)
            return []

    def search_with_context(
        self,
        query: str,
        top_k: int = 8,
        min_score: float = 0.3,
        use_mmr: bool = False,
        lambda_mmr: float = 0.7,
        fetch_k: int = 15
    ) -> List[Dict[str, Any]]:
        """
        Search for documents with more context for RAG synthesis.

        Args:
            query: The search query
            top_k: Number of results to return (default 8 for better RAG context)
            min_score: Minimum relevance score (0-1, filter out poor matches)
            use_mmr: Whether to apply MMR for diversity
            lambda_mmr: Balance between relevance and diversity (0=diversity, 1=relevance)
            fetch_k: Number of candidates to fetch for MMR selection

        Returns:
            List of dicts with 'content', 'score', 'source', filtered by min_score
        """
        if use_mmr:
            all_results = self.search_with_mmr(query, top_k=top_k, fetch_k=fetch_k, lambda_mult=lambda_mmr)
        else:
            all_results = self.search(query, top_k=top_k)

        if not all_results:
            return []

        initial_count = len(all_results)

        # Filter by min_score
        filtered_results = [r for r in all_results if r['score'] >= min_score]

        # If fewer than 3 results after filtering, return top 3 regardless of score
        # This ensures some context is always available for RAG synthesis
        if len(filtered_results) < 3 and len(all_results) >= 3:
            logger.info(f"FAISS search_with_context: only {len(filtered_results)} results above min_score={min_score}, returning top 3")
            filtered_results = all_results[:3]
        elif len(filtered_results) < 3:
            # Return whatever we have if fewer than 3 total results
            filtered_results = all_results

        logger.info(f"FAISS search_with_context: {initial_count} results -> {len(filtered_results)} after filtering (min_score={min_score}, mmr={use_mmr})")
        return filtered_results

    def search_with_mmr(
        self,
        query: str,
        top_k: int = 5,
        fetch_k: int = 20,
        lambda_mult: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Search with Maximal Marginal Relevance for diversity.

        MMR balances relevance (how well a document matches the query) with
        diversity (how different it is from already selected documents).

        Args:
            query: Search query
            top_k: Number of results to return
            fetch_k: Number of candidates to fetch before MMR selection
            lambda_mult: Diversity factor (0=max diversity, 1=max relevance)

        Returns:
            Diverse, relevant documents
        """
        if not self._initialized and not self.initialize():
            logger.warning("FAISS service not initialized, returning empty results")
            return []

        try:
            import numpy as np

            # Generate embedding for the query
            query_embedding = self.embeddings_model.embed_query(query)
            query_vector = np.array([query_embedding]).astype('float32')

            # Fetch more candidates than needed for MMR selection
            distances, indices = self.index.search(query_vector, fetch_k)

            # Collect candidates with their embeddings
            candidates = []
            for i, idx in enumerate(indices[0]):
                if idx == -1:
                    continue

                doc = self._get_document(idx)
                if doc is None:
                    continue

                # Get document content and metadata
                if isinstance(doc, dict):
                    content = doc.get('text', doc.get('content', doc.get('page_content', str(doc))))
                    source = doc.get('source', doc.get('metadata', {}).get('source', 'Knowledge Base'))
                elif hasattr(doc, 'page_content'):
                    content = doc.page_content
                    source = getattr(doc, 'metadata', {}).get('source', 'Knowledge Base')
                else:
                    content = str(doc)
                    source = 'Knowledge Base'

                # Get embedding for MMR calculation
                # Note: We regenerate embeddings since we don't store them
                doc_embedding = self.embeddings_model.embed_query(content[:500])

                distance = float(distances[0][i])
                score = 1 / (1 + distance)

                candidates.append({
                    'content': content,
                    'source': source,
                    'score': round(score, 3),
                    'index': int(idx),
                    'embedding': np.array(doc_embedding)
                })

            if not candidates:
                return []

            # Apply MMR selection
            selected = []
            selected_embeddings = []
            query_emb = np.array(query_embedding)

            while len(selected) < top_k and candidates:
                if not selected:
                    # First selection: most relevant (highest score)
                    best = max(candidates, key=lambda x: x['score'])
                else:
                    # Subsequent: balance relevance and diversity
                    best_mmr = -float('inf')
                    best = None

                    for candidate in candidates:
                        # Relevance: similarity to query (use score)
                        relevance = candidate['score']

                        # Diversity: max similarity to already selected docs
                        if selected_embeddings:
                            similarities = []
                            for sel_emb in selected_embeddings:
                                # Cosine similarity
                                dot = np.dot(candidate['embedding'], sel_emb)
                                norm = np.linalg.norm(candidate['embedding']) * np.linalg.norm(sel_emb)
                                if norm > 0:
                                    similarities.append(dot / norm)
                                else:
                                    similarities.append(0)
                            max_sim = max(similarities)
                        else:
                            max_sim = 0

                        # MMR score: lambda * relevance - (1-lambda) * similarity_to_selected
                        mmr_score = lambda_mult * relevance - (1 - lambda_mult) * max_sim

                        if mmr_score > best_mmr:
                            best_mmr = mmr_score
                            best = candidate

                if best:
                    # Remove embedding before adding to results (not needed in output)
                    selected_embeddings.append(best['embedding'])
                    result = {k: v for k, v in best.items() if k != 'embedding'}
                    selected.append(result)
                    candidates.remove(best)

            logger.info(f"FAISS MMR search for '{query[:50]}...' returned {len(selected)} diverse results")
            return selected

        except Exception as e:
            logger.error(f"FAISS MMR search failed: {e}", exc_info=True)
            # Fall back to regular search
            return self.search(query, top_k=top_k)

    def get_status(self) -> Dict[str, Any]:
        """Get service status"""
        doc_count = len(self.index_to_docstore_id) if self.index_to_docstore_id else 0
        return {
            'initialized': self._initialized,
            'error': self._init_error,
            'vector_count': self.index.ntotal if self.index else 0,
            'document_count': doc_count,
            'bucket': GCS_BUCKET_NAME,
            'index_path': f"{GCS_INDEX_PREFIX}{GCS_INDEX_FILE}",
            'cache_dir': str(CACHE_DIR)
        }


# Singleton instance
_faiss_service = None


def get_faiss_helpdesk_service() -> FAISSHelpdeskService:
    """Get the singleton FAISS helpdesk service instance"""
    global _faiss_service
    if _faiss_service is None:
        _faiss_service = FAISSHelpdeskService()
    return _faiss_service


async def initialize_faiss_service():
    """Initialize the FAISS service (call on app startup)"""
    service = get_faiss_helpdesk_service()
    return service.initialize()


def reset_faiss_service(clear_cache: bool = False):
    """
    Reset the FAISS service singleton for reinitialization.

    Args:
        clear_cache: If True, also delete cached index files to force re-download
    """
    global _faiss_service

    if clear_cache:
        import shutil
        if CACHE_DIR.exists():
            shutil.rmtree(CACHE_DIR)
            logger.info(f"Cleared FAISS cache at {CACHE_DIR}")
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Reset the singleton
    if _faiss_service is not None:
        FAISSHelpdeskService._instance = None
        _faiss_service = None
        logger.info("FAISS service singleton reset")

    return True


if __name__ == "__main__":
    # Test script for search_with_context
    print("Testing FAISS Helpdesk Service - search_with_context")
    print("=" * 60)

    service = FAISSHelpdeskService()
    if service.initialize():
        print("Service initialized successfully\n")

        # Test search_with_context
        results = service.search_with_context("Maldives hotels with pool", top_k=8, min_score=0.3)
        print(f"Found {len(results)} relevant documents\n")

        for i, r in enumerate(results[:3]):
            print(f"Result {i+1}:")
            print(f"  Score: {r['score']:.3f}")
            print(f"  Source: {r['source']}")
            print(f"  Content: {r['content'][:100]}...")
            print()
    else:
        print("Failed to initialize FAISS service")
