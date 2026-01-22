"""
GCS and FAISS Mock Infrastructure

Reusable mock classes for testing Google Cloud Storage and FAISS-dependent code:
- MockGCSBlob - Simulates GCS blob objects
- MockGCSBucket - Simulates GCS bucket with blob management
- MockGCSClient - Full client mock with configurable responses
- MockFAISSIndex - Simulates FAISS vector index
- MockDocstore - Simulates LangChain InMemoryDocstore
- MockSentenceTransformer - Simulates embedding model
- Factory functions and generators

Usage:
    from tests.fixtures.gcs_fixtures import (
        create_mock_gcs_client,
        create_mock_faiss_service,
        MockFAISSIndex,
        MockSentenceTransformer,
    )

    # Create mock GCS client with pre-configured blobs
    mock_client = create_mock_gcs_client([
        {"name": "documents/doc1.txt", "content": "Hello world"},
        {"name": "documents/doc2.txt", "content": "Test content"},
    ])

    # Use in tests with patch
    with patch('google.cloud.storage.Client', return_value=mock_client):
        # Your test code here
        pass
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Iterator
from unittest.mock import MagicMock
import numpy as np


# ==================== GCS Mock Classes ====================

class MockGCSBlob:
    """
    Simulates a Google Cloud Storage blob object.

    Attributes:
        name: Full blob path (e.g., "documents/doc1.txt")
        size: Blob size in bytes
        metadata: Custom metadata dictionary
        time_created: Creation timestamp
        updated: Last update timestamp

    Example:
        blob = MockGCSBlob("documents/doc1.txt", content="Hello world")
        assert blob.exists() == True
        content = blob.download_as_text()
        assert content == "Hello world"
    """

    def __init__(
        self,
        name: str,
        content: Optional[str] = None,
        content_bytes: Optional[bytes] = None,
        metadata: Optional[Dict[str, str]] = None,
        size: Optional[int] = None,
        exists: bool = True
    ):
        self.name = name
        self._content = content
        self._content_bytes = content_bytes or (content.encode('utf-8') if content else None)
        self.metadata = metadata or {}
        self._exists = exists
        self.time_created = datetime.utcnow() - timedelta(days=random.randint(1, 30))
        self.updated = datetime.utcnow()
        self.size = size or (len(self._content_bytes) if self._content_bytes else 0)
        self._download_count = 0
        self._upload_count = 0

    def exists(self) -> bool:
        """Check if blob exists."""
        return self._exists

    def download_to_filename(self, filename: str) -> None:
        """
        Download blob content to a local file.

        Args:
            filename: Local file path to save content
        """
        if not self._exists:
            raise Exception(f"Blob {self.name} does not exist")

        self._download_count += 1
        content = self._content_bytes or b""
        with open(filename, 'wb') as f:
            f.write(content)

    def download_as_text(self, encoding: str = 'utf-8') -> str:
        """
        Download blob content as text.

        Args:
            encoding: Text encoding (default: utf-8)

        Returns:
            Blob content as string
        """
        if not self._exists:
            raise Exception(f"Blob {self.name} does not exist")

        self._download_count += 1
        if self._content is not None:
            return self._content
        if self._content_bytes:
            return self._content_bytes.decode(encoding)
        return ""

    def download_as_bytes(self) -> bytes:
        """Download blob content as bytes."""
        if not self._exists:
            raise Exception(f"Blob {self.name} does not exist")

        self._download_count += 1
        return self._content_bytes or b""

    def upload_from_string(
        self,
        data: str,
        content_type: str = 'text/plain'
    ) -> None:
        """
        Upload content from string.

        Args:
            data: String content to upload
            content_type: MIME content type
        """
        self._content = data
        self._content_bytes = data.encode('utf-8')
        self.size = len(self._content_bytes)
        self._exists = True
        self.updated = datetime.utcnow()
        self._upload_count += 1

    def upload_from_filename(self, filename: str) -> None:
        """
        Upload content from local file.

        Args:
            filename: Local file path
        """
        with open(filename, 'rb') as f:
            self._content_bytes = f.read()
        self._content = None
        self.size = len(self._content_bytes)
        self._exists = True
        self.updated = datetime.utcnow()
        self._upload_count += 1

    def delete(self) -> None:
        """Delete the blob."""
        self._exists = False
        self._content = None
        self._content_bytes = None

    def __repr__(self) -> str:
        return f"MockGCSBlob(name={self.name!r}, size={self.size}, exists={self._exists})"


class MockGCSBucket:
    """
    Simulates a Google Cloud Storage bucket.

    Attributes:
        name: Bucket name

    Example:
        bucket = MockGCSBucket("my-bucket")
        bucket.add_blob("docs/file.txt", "Content here")
        blob = bucket.blob("docs/file.txt")
        assert blob.exists() == True
    """

    def __init__(self, name: str):
        self.name = name
        self._blobs: Dict[str, MockGCSBlob] = {}

    def add_blob(
        self,
        name: str,
        content: Optional[str] = None,
        content_bytes: Optional[bytes] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> MockGCSBlob:
        """
        Add a blob to the bucket.

        Args:
            name: Blob name/path
            content: Text content
            content_bytes: Binary content
            metadata: Custom metadata

        Returns:
            Created MockGCSBlob
        """
        blob = MockGCSBlob(
            name=name,
            content=content,
            content_bytes=content_bytes,
            metadata=metadata
        )
        self._blobs[name] = blob
        return blob

    def blob(self, name: str) -> MockGCSBlob:
        """
        Get a blob reference by name.

        Args:
            name: Blob name/path

        Returns:
            MockGCSBlob (may not exist)
        """
        if name in self._blobs:
            return self._blobs[name]
        # Return non-existent blob reference
        return MockGCSBlob(name=name, exists=False)

    def list_blobs(
        self,
        prefix: Optional[str] = None,
        max_results: Optional[int] = None
    ) -> Iterator[MockGCSBlob]:
        """
        List blobs in the bucket with optional prefix filter.

        Args:
            prefix: Filter blobs by name prefix
            max_results: Maximum number of results

        Returns:
            Iterator of MockGCSBlob objects
        """
        blobs = []
        for name, blob in self._blobs.items():
            if prefix is None or name.startswith(prefix):
                if blob._exists:
                    blobs.append(blob)

        if max_results:
            blobs = blobs[:max_results]

        return iter(blobs)

    def __repr__(self) -> str:
        return f"MockGCSBucket(name={self.name!r}, blobs={len(self._blobs)})"


class MockGCSClient:
    """
    Full mock of google.cloud.storage.Client.

    Supports:
    - bucket() method to get bucket references
    - Pre-configured buckets and blobs
    - Operation tracking for assertions

    Example:
        client = MockGCSClient()
        client.add_bucket("my-bucket", blobs=[
            {"name": "doc.txt", "content": "Hello"}
        ])
        bucket = client.bucket("my-bucket")
        blob = bucket.blob("doc.txt")
        content = blob.download_as_text()
    """

    def __init__(self, project: str = "test-project"):
        self.project = project
        self._buckets: Dict[str, MockGCSBucket] = {}
        self._operation_history: List[Dict[str, Any]] = []

    def add_bucket(
        self,
        name: str,
        blobs: Optional[List[Dict[str, Any]]] = None
    ) -> MockGCSBucket:
        """
        Add a bucket with optional pre-configured blobs.

        Args:
            name: Bucket name
            blobs: List of blob configurations

        Returns:
            Created MockGCSBucket
        """
        bucket = MockGCSBucket(name)

        if blobs:
            for blob_config in blobs:
                bucket.add_blob(
                    name=blob_config.get("name", ""),
                    content=blob_config.get("content"),
                    content_bytes=blob_config.get("content_bytes"),
                    metadata=blob_config.get("metadata")
                )

        self._buckets[name] = bucket
        return bucket

    def bucket(self, name: str) -> MockGCSBucket:
        """
        Get a bucket reference by name.

        Args:
            name: Bucket name

        Returns:
            MockGCSBucket (creates empty if not exists)
        """
        self._operation_history.append({
            "operation": "bucket",
            "bucket_name": name,
            "timestamp": datetime.utcnow().isoformat()
        })

        if name not in self._buckets:
            self._buckets[name] = MockGCSBucket(name)

        return self._buckets[name]

    def get_operation_history(self) -> List[Dict[str, Any]]:
        """Return list of all operations performed."""
        return self._operation_history.copy()

    def __repr__(self) -> str:
        return f"MockGCSClient(project={self.project!r}, buckets={len(self._buckets)})"


# ==================== FAISS Mock Classes ====================

class MockFAISSIndex:
    """
    Simulates a FAISS vector index.

    Attributes:
        ntotal: Number of vectors in the index
        d: Vector dimension

    Example:
        index = MockFAISSIndex(ntotal=100, dimension=768)
        distances, indices = index.search(query_vector, k=5)
        # Returns 5 nearest neighbors
    """

    def __init__(
        self,
        ntotal: int = 100,
        dimension: int = 768,
        search_results: Optional[Tuple[np.ndarray, np.ndarray]] = None
    ):
        self.ntotal = ntotal
        self.d = dimension
        self._search_results = search_results
        self._search_count = 0

    def search(
        self,
        query_vector: np.ndarray,
        k: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Search for k nearest neighbors.

        Args:
            query_vector: Query embedding(s) of shape (n_queries, d)
            k: Number of neighbors to return

        Returns:
            Tuple of (distances, indices) arrays
        """
        self._search_count += 1

        if self._search_results is not None:
            return self._search_results

        # Generate mock results
        n_queries = query_vector.shape[0]
        actual_k = min(k, self.ntotal)

        # Random indices (unique per query)
        indices = np.array([
            np.random.choice(self.ntotal, size=actual_k, replace=False)
            for _ in range(n_queries)
        ])

        # Distances (L2, so 0 is best)
        distances = np.random.uniform(0.1, 2.0, size=(n_queries, actual_k))
        distances = np.sort(distances, axis=1)  # Sort ascending

        return distances.astype('float32'), indices.astype('int64')

    def add(self, vectors: np.ndarray) -> None:
        """Add vectors to the index."""
        self.ntotal += vectors.shape[0]

    def __repr__(self) -> str:
        return f"MockFAISSIndex(ntotal={self.ntotal}, d={self.d})"


class MockDocstore:
    """
    Simulates LangChain InMemoryDocstore.

    Stores documents that can be retrieved by ID.

    Example:
        docstore = MockDocstore()
        docstore.add_documents([
            {"id": "0", "page_content": "Document 1", "metadata": {"source": "file1.txt"}}
        ])
        doc = docstore.search("0")
        assert doc.page_content == "Document 1"
    """

    def __init__(self, documents: Optional[Dict[str, Any]] = None):
        self._dict: Dict[str, Any] = documents or {}

    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add documents to the docstore.

        Args:
            documents: List of document dictionaries with 'id', 'page_content', 'metadata'
        """
        for doc in documents:
            doc_id = doc.get("id", str(len(self._dict)))
            self._dict[doc_id] = MockDocument(
                page_content=doc.get("page_content", doc.get("content", "")),
                metadata=doc.get("metadata", {})
            )

    def search(self, doc_id: str) -> Any:
        """
        Search for a document by ID.

        Args:
            doc_id: Document ID

        Returns:
            Document or "Document not found" message
        """
        if doc_id in self._dict:
            return self._dict[doc_id]
        return f"Document {doc_id} not found"

    def __repr__(self) -> str:
        return f"MockDocstore(documents={len(self._dict)})"


class MockDocument:
    """
    Simulates a LangChain Document object.

    Attributes:
        page_content: Document text content
        metadata: Document metadata dictionary
    """

    def __init__(self, page_content: str = "", metadata: Optional[Dict[str, Any]] = None):
        self.page_content = page_content
        self.metadata = metadata or {}

    def __repr__(self) -> str:
        return f"MockDocument(content={self.page_content[:50]!r}...)"


class MockSentenceTransformer:
    """
    Simulates sentence-transformers SentenceTransformer model.

    Generates deterministic embeddings for testing.

    Example:
        model = MockSentenceTransformer(dimension=768)
        embedding = model.embed_query("test query")
        assert len(embedding) == 768
    """

    def __init__(self, dimension: int = 768):
        self.dimension = dimension
        self._embed_count = 0

    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Input text

        Returns:
            Embedding vector as list of floats
        """
        self._embed_count += 1
        return generate_mock_embedding(self.dimension, seed=hash(text))

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        self._embed_count += len(texts)
        return [generate_mock_embedding(self.dimension, seed=hash(t)) for t in texts]

    def encode(
        self,
        texts: Any,
        show_progress_bar: bool = False
    ) -> np.ndarray:
        """
        Encode texts (compatible with SentenceTransformer.encode).

        Args:
            texts: Single text or list of texts
            show_progress_bar: Ignored in mock

        Returns:
            Numpy array of embeddings
        """
        if isinstance(texts, str):
            return np.array(self.embed_query(texts))
        return np.array(self.embed_documents(texts))

    def __repr__(self) -> str:
        return f"MockSentenceTransformer(dimension={self.dimension})"


# ==================== Factory Functions ====================

def create_mock_gcs_client(
    blobs: Optional[List[Dict[str, Any]]] = None,
    bucket_name: str = "test-bucket",
    project: str = "test-project"
) -> MockGCSClient:
    """
    Create a configured MockGCSClient.

    Args:
        blobs: List of blob configurations to add to default bucket
        bucket_name: Name of default bucket
        project: GCP project ID

    Returns:
        Configured MockGCSClient instance

    Example:
        # Client with documents
        client = create_mock_gcs_client([
            {"name": "documents/doc1.txt", "content": "Hello world"},
            {"name": "documents/doc2.txt", "content": "Test content"},
        ])

        bucket = client.bucket("test-bucket")
        blob = bucket.blob("documents/doc1.txt")
        content = blob.download_as_text()
    """
    client = MockGCSClient(project=project)
    client.add_bucket(bucket_name, blobs=blobs)
    return client


def create_mock_faiss_service(
    vectors: int = 100,
    documents: Optional[List[Dict[str, Any]]] = None,
    dimension: int = 768
) -> Dict[str, Any]:
    """
    Create mock FAISS service components.

    Args:
        vectors: Number of vectors in index
        documents: List of document dicts with 'content', 'source', 'metadata'
        dimension: Embedding dimension

    Returns:
        Dict with 'index', 'docstore', 'index_to_docstore_id', 'embeddings_model'

    Example:
        service = create_mock_faiss_service(
            vectors=50,
            documents=[
                {"content": "Document 1", "source": "file1.txt"},
                {"content": "Document 2", "source": "file2.txt"},
            ]
        )
        index = service['index']
        docstore = service['docstore']
    """
    # Create index
    index = MockFAISSIndex(ntotal=vectors, dimension=dimension)

    # Create docstore with documents
    docstore = MockDocstore()
    index_to_docstore_id = {}

    if documents:
        for i, doc in enumerate(documents):
            doc_id = str(i)
            index_to_docstore_id[i] = doc_id
            docstore._dict[doc_id] = MockDocument(
                page_content=doc.get("content", doc.get("page_content", "")),
                metadata={
                    "source": doc.get("source", "test-source"),
                    **doc.get("metadata", {})
                }
            )
    else:
        # Generate default documents
        for i in range(min(vectors, 10)):
            doc_id = str(i)
            index_to_docstore_id[i] = doc_id
            docstore._dict[doc_id] = MockDocument(
                page_content=f"Document {i} content about travel and hotels.",
                metadata={"source": f"document_{i}.txt"}
            )

    # Create embeddings model
    embeddings_model = MockSentenceTransformer(dimension=dimension)

    return {
        'index': index,
        'docstore': docstore,
        'index_to_docstore_id': index_to_docstore_id,
        'embeddings_model': embeddings_model
    }


def create_mock_rag_corpus_response(
    results: Optional[List[Dict[str, Any]]] = None,
    num_results: int = 5
) -> MagicMock:
    """
    Create a mock Vertex AI RAG retrieval_query response.

    Args:
        results: List of result dicts with 'text', 'source_uri'
        num_results: Number of results if not provided

    Returns:
        Mock response object with contexts attribute

    Example:
        response = create_mock_rag_corpus_response([
            {"text": "Hotel info here", "source_uri": "gs://bucket/hotels.txt"},
            {"text": "More info", "source_uri": "gs://bucket/more.txt"},
        ])
        assert len(response.contexts) == 2
    """
    if results is None:
        results = [
            {
                "text": f"Result {i}: Information about travel destination {i}.",
                "source_uri": f"gs://bucket/document_{i}.txt"
            }
            for i in range(num_results)
        ]

    # Create mock context objects
    contexts = []
    for result in results:
        context = MagicMock()
        context.text = result.get("text", "")
        context.source_uri = result.get("source_uri", "")
        contexts.append(context)

    # Create response
    response = MagicMock()
    response.contexts = contexts

    return response


# ==================== Helper Generators ====================

def generate_mock_embedding(dim: int = 768, seed: Optional[int] = None) -> List[float]:
    """
    Generate a mock embedding vector.

    Args:
        dim: Embedding dimension
        seed: Random seed for reproducibility

    Returns:
        Normalized embedding vector as list of floats

    Example:
        embedding = generate_mock_embedding(768)
        assert len(embedding) == 768
        # Roughly normalized
        assert 0.9 < sum(x**2 for x in embedding)**0.5 < 1.1
    """
    if seed is not None:
        np.random.seed(seed % (2**31))

    # Generate random vector
    vec = np.random.randn(dim).astype('float32')

    # Normalize to unit length
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm

    return vec.tolist()


def generate_mock_search_results(
    count: int = 5,
    min_score: float = 0.3,
    max_score: float = 0.95
) -> List[Dict[str, Any]]:
    """
    Generate mock FAISS search results.

    Args:
        count: Number of results to generate
        min_score: Minimum relevance score
        max_score: Maximum relevance score

    Returns:
        List of result dictionaries with 'content', 'source', 'score', 'index'

    Example:
        results = generate_mock_search_results(5)
        for r in results:
            assert 'content' in r
            assert 'score' in r
            assert 0 <= r['score'] <= 1
    """
    topics = [
        "luxury beach resort amenities",
        "travel visa requirements",
        "hotel booking process",
        "destination highlights",
        "local cuisine recommendations",
        "transportation options",
        "weather and best times to visit",
        "cultural attractions",
        "water sports activities",
        "spa and wellness services",
    ]

    results = []
    scores = np.linspace(max_score, min_score, count)

    for i in range(count):
        topic = topics[i % len(topics)]
        results.append({
            "content": f"Information about {topic}. This document contains detailed "
                      f"information that travelers need to know.",
            "source": f"knowledge_base/{topic.replace(' ', '_')}.txt",
            "score": round(float(scores[i]), 3),
            "index": i
        })

    return results


def generate_mock_documents(
    count: int = 10,
    categories: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Generate mock knowledge base documents.

    Args:
        count: Number of documents to generate
        categories: List of categories to use

    Returns:
        List of document dictionaries

    Example:
        docs = generate_mock_documents(5)
        for doc in docs:
            assert 'id' in doc
            assert 'content' in doc
    """
    if categories is None:
        categories = ["hotels", "destinations", "activities", "travel_tips", "general"]

    documents = []
    for i in range(count):
        category = categories[i % len(categories)]
        documents.append({
            "id": f"doc_{i:04d}",
            "title": f"Document {i}: {category.title()} Guide",
            "content": f"This is document {i} about {category}. It contains useful "
                      f"information for travelers looking for {category} information.",
            "category": category,
            "source": f"documents/{category}/doc_{i}.txt",
            "metadata": {
                "category": category,
                "created_at": (datetime.utcnow() - timedelta(days=i)).isoformat(),
                "visibility": "public"
            }
        })

    return documents


# ==================== Pre-configured Response Templates ====================

# Default GCS bucket configuration for knowledge base
KNOWLEDGE_BUCKET_CONFIG = {
    "bucket_name": "zorah-475411-rag-documents",
    "index_prefix": "faiss_indexes/",
    "documents_prefix": "documents/",
    "files": [
        {"name": "faiss_indexes/index.faiss", "content_bytes": b"FAISS_INDEX_MOCK"},
        {"name": "faiss_indexes/index.pkl", "content_bytes": b"METADATA_MOCK"},
    ]
}

# Sample search results for testing
SAMPLE_SEARCH_RESULTS = [
    {
        "content": "The Maldives offers some of the world's most luxurious overwater villas with direct ocean access.",
        "source": "destinations/maldives.txt",
        "score": 0.92,
        "index": 0
    },
    {
        "content": "Mauritius combines beautiful beaches with diverse cultural heritage and excellent cuisine.",
        "source": "destinations/mauritius.txt",
        "score": 0.87,
        "index": 1
    },
    {
        "content": "Seychelles features 115 islands with granite boulders and pristine beaches.",
        "source": "destinations/seychelles.txt",
        "score": 0.81,
        "index": 2
    },
]
