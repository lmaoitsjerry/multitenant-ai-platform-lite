"""
Knowledge Base API Routes

Manages document uploads, FAISS indexing, and knowledge search.
Per-tenant document storage and vector indexes.

Endpoints:
- /api/v1/knowledge/documents - Document CRUD
- /api/v1/knowledge/search - Search knowledge base
- /api/v1/knowledge/status - Index status
"""

import logging
import uuid
import os
import json
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Header, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from config.loader import ClientConfig
from src.utils.error_handler import log_and_raise

logger = logging.getLogger(__name__)

# ==================== Router ====================

knowledge_router = APIRouter(prefix="/api/v1/knowledge", tags=["Knowledge Base"])


# ==================== Pydantic Models ====================

class DocumentMetadata(BaseModel):
    """Document metadata"""
    document_id: str
    filename: str
    category: str
    tags: List[str] = []
    visibility: str = "public"  # public (inbound agent) or private (helpdesk only)
    file_type: str
    file_size: int
    status: str  # pending, indexed, error
    chunk_count: int = 0
    uploaded_at: str
    indexed_at: Optional[str] = None
    error_message: Optional[str] = None


class DocumentUpload(BaseModel):
    """Document upload request"""
    category: str = "general"
    tags: List[str] = []
    visibility: str = "public"
    auto_index: bool = True


class SearchRequest(BaseModel):
    """Knowledge search request"""
    query: str
    top_k: int = Field(default=5, ge=1, le=20)
    category: Optional[str] = None
    visibility: Optional[str] = None  # Filter by visibility
    min_score: float = Field(default=0.5, ge=0, le=1)


class SearchResult(BaseModel):
    """Search result"""
    content: str
    source: str
    score: float
    document_id: str
    chunk_index: int


# ==================== Dependency ====================

_client_configs = {}

def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    import os
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")

    if client_id not in _client_configs:
        try:
            _client_configs[client_id] = ClientConfig(client_id)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid client: {client_id}")

    return _client_configs[client_id]


# ==================== FAISS Index Manager ====================

class FAISSIndexManager:
    """Manages per-tenant FAISS indexes"""

    def __init__(self, config: ClientConfig):
        self.config = config
        self.client_id = config.client_id

        # Paths
        self.base_path = Path(f"clients/{self.client_id}/data/knowledge")
        self.documents_path = self.base_path / "documents"
        self.index_path = self.base_path / "faiss_index"
        self.metadata_file = self.base_path / "metadata.json"

        # Ensure directories exist
        self.documents_path.mkdir(parents=True, exist_ok=True)
        self.index_path.mkdir(parents=True, exist_ok=True)

        # Load or create metadata
        self.metadata = self._load_metadata()

        # FAISS index (lazy loaded)
        self._index = None
        self._embeddings = None

    def _load_metadata(self) -> Dict:
        """Load document metadata"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r') as f:
                data = json.load(f)
                # Migration: add visibility field to existing documents
                for doc_id, doc in data.get("documents", {}).items():
                    if "visibility" not in doc:
                        doc["visibility"] = "public"
                return data
        return {"documents": {}, "chunks": [], "last_updated": None}

    def _save_metadata(self):
        """Save document metadata"""
        self.metadata["last_updated"] = datetime.utcnow().isoformat()
        with open(self.metadata_file, 'w') as f:
            json.dump(self.metadata, f, indent=2)

    def _get_embeddings_model(self):
        """Get embeddings model"""
        if self._embeddings is None:
            try:
                # Try sentence-transformers first
                from sentence_transformers import SentenceTransformer
                self._embeddings = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Using sentence-transformers for embeddings")
            except ImportError:
                try:
                    # Fall back to OpenAI
                    import openai
                    self._embeddings = "openai"
                    logger.info("Using OpenAI for embeddings")
                except ImportError:
                    logger.error("No embeddings model available")
                    raise HTTPException(status_code=500, detail="No embeddings model available")
        return self._embeddings

    def _embed_text(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts"""
        model = self._get_embeddings_model()

        if model == "openai":
            import openai
            response = openai.embeddings.create(
                model="text-embedding-ada-002",
                input=texts
            )
            return [e.embedding for e in response.data]
        else:
            # sentence-transformers
            embeddings = model.encode(texts, convert_to_numpy=True)
            return embeddings.tolist()

    def _extract_text(self, file_path: Path, file_type: str) -> str:
        """Extract text from document"""
        text = ""

        if file_type in ['txt', 'md']:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

        elif file_type == 'pdf':
            try:
                import pypdf
                reader = pypdf.PdfReader(str(file_path))
                text = "\n".join(page.extract_text() for page in reader.pages)
            except ImportError:
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(str(file_path))
                    text = "\n".join(page.get_text() for page in doc)
                except ImportError:
                    raise HTTPException(status_code=500, detail="No PDF library available (install pypdf or pymupdf)")

        elif file_type == 'docx':
            try:
                from docx import Document
                doc = Document(str(file_path))
                text = "\n".join(para.text for para in doc.paragraphs)
            except ImportError:
                raise HTTPException(status_code=500, detail="python-docx not installed")

        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

        return text

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into chunks"""
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)

        return chunks

    def add_document(
        self,
        file: UploadFile,
        category: str = "general",
        tags: List[str] = None,
        visibility: str = "public"
    ) -> DocumentMetadata:
        """Add a document to the knowledge base"""

        # Validate visibility
        if visibility not in ["public", "private"]:
            visibility = "public"

        # Generate document ID
        document_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"

        # Determine file type
        filename = file.filename
        file_type = filename.split('.')[-1].lower()

        if file_type not in ['txt', 'md', 'pdf', 'docx']:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_type}")

        # Save file
        file_path = self.documents_path / f"{document_id}.{file_type}"
        content = file.file.read()

        with open(file_path, 'wb') as f:
            f.write(content)

        # Create metadata
        doc_metadata = {
            "document_id": document_id,
            "filename": filename,
            "category": category,
            "tags": tags or [],
            "visibility": visibility,
            "file_type": file_type,
            "file_size": len(content),
            "file_path": str(file_path),
            "status": "pending",
            "chunk_count": 0,
            "uploaded_at": datetime.utcnow().isoformat(),
            "indexed_at": None,
            "error_message": None
        }

        self.metadata["documents"][document_id] = doc_metadata
        self._save_metadata()

        return DocumentMetadata(**doc_metadata)

    def index_document(self, document_id: str) -> DocumentMetadata:
        """Index a document into FAISS"""

        if document_id not in self.metadata["documents"]:
            raise HTTPException(status_code=404, detail="Document not found")

        doc = self.metadata["documents"][document_id]

        try:
            # Extract text
            file_path = Path(doc["file_path"])
            text = self._extract_text(file_path, doc["file_type"])

            # Chunk text
            chunks = self._chunk_text(text)

            if not chunks:
                raise ValueError("No content extracted from document")

            # Generate embeddings
            embeddings = self._embed_text(chunks)

            # Load or create FAISS index
            import faiss
            import numpy as np

            index_file = self.index_path / "index.faiss"
            chunks_file = self.index_path / "chunks.json"

            dimension = len(embeddings[0])

            if index_file.exists():
                index = faiss.read_index(str(index_file))
                with open(chunks_file, 'r') as f:
                    all_chunks = json.load(f)
            else:
                index = faiss.IndexFlatL2(dimension)
                all_chunks = []

            # Add to index
            start_idx = len(all_chunks)
            vectors = np.array(embeddings).astype('float32')
            index.add(vectors)

            # Add chunk metadata (including visibility)
            for i, chunk in enumerate(chunks):
                all_chunks.append({
                    "document_id": document_id,
                    "chunk_index": i,
                    "content": chunk,
                    "category": doc["category"],
                    "visibility": doc.get("visibility", "public")
                })

            # Save index
            faiss.write_index(index, str(index_file))
            with open(chunks_file, 'w') as f:
                json.dump(all_chunks, f)

            # Update metadata
            doc["status"] = "indexed"
            doc["chunk_count"] = len(chunks)
            doc["indexed_at"] = datetime.utcnow().isoformat()
            doc["error_message"] = None

            self.metadata["chunks"] = all_chunks
            self._save_metadata()

            logger.info(f"Indexed document {document_id}: {len(chunks)} chunks, visibility: {doc.get('visibility', 'public')}")

            return DocumentMetadata(**doc)

        except Exception as e:
            logger.error(f"Failed to index document {document_id}: {e}")
            doc["status"] = "error"
            doc["error_message"] = str(e)
            self._save_metadata()
            log_and_raise(500, f"indexing document {document_id}", e, logger)

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        visibility: Optional[str] = None,
        min_score: float = 0.5
    ) -> List[Dict]:
        """Search the knowledge base"""

        index_file = self.index_path / "index.faiss"
        chunks_file = self.index_path / "chunks.json"

        if not index_file.exists():
            return []

        try:
            import faiss
            import numpy as np

            # Load index
            index = faiss.read_index(str(index_file))
            with open(chunks_file, 'r') as f:
                all_chunks = json.load(f)

            # Embed query
            query_embedding = self._embed_text([query])[0]
            query_vector = np.array([query_embedding]).astype('float32')

            # Search
            distances, indices = index.search(query_vector, min(top_k * 2, len(all_chunks)))

            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(all_chunks):
                    continue

                chunk = all_chunks[idx]

                # Filter by category
                if category and chunk.get("category") != category:
                    continue

                # Filter by visibility
                if visibility and chunk.get("visibility", "public") != visibility:
                    continue

                # Convert distance to similarity score (L2 distance)
                score = 1 / (1 + dist)

                if score >= min_score:
                    results.append({
                        "content": chunk["content"],
                        "source": self.metadata["documents"].get(chunk["document_id"], {}).get("filename", "Unknown"),
                        "score": round(score, 3),
                        "document_id": chunk["document_id"],
                        "chunk_index": chunk["chunk_index"],
                        "visibility": chunk.get("visibility", "public")
                    })

                if len(results) >= top_k:
                    break

            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_documents(self, visibility: Optional[str] = None) -> List[DocumentMetadata]:
        """Get all documents, optionally filtered by visibility"""
        docs = [DocumentMetadata(**doc) for doc in self.metadata["documents"].values()]
        if visibility:
            docs = [d for d in docs if d.visibility == visibility]
        return docs

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """Get document by ID"""
        doc = self.metadata["documents"].get(document_id)
        if doc:
            return DocumentMetadata(**doc)
        return None

    def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        if document_id not in self.metadata["documents"]:
            return False

        doc = self.metadata["documents"][document_id]

        # Delete file
        file_path = Path(doc["file_path"])
        if file_path.exists():
            file_path.unlink()

        # Remove from metadata
        del self.metadata["documents"][document_id]

        # Remove chunks and rebuild index
        self._rebuild_index()

        self._save_metadata()
        return True

    def _rebuild_index(self):
        """Rebuild FAISS index from remaining documents"""
        try:
            import faiss
            import numpy as np

            all_chunks = []
            all_embeddings = []

            for doc_id, doc in self.metadata["documents"].items():
                if doc["status"] != "indexed":
                    continue

                file_path = Path(doc["file_path"])
                if not file_path.exists():
                    continue

                text = self._extract_text(file_path, doc["file_type"])
                chunks = self._chunk_text(text)
                embeddings = self._embed_text(chunks)

                for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                    all_chunks.append({
                        "document_id": doc_id,
                        "chunk_index": i,
                        "content": chunk,
                        "category": doc["category"],
                        "visibility": doc.get("visibility", "public")
                    })
                    all_embeddings.append(emb)

            index_file = self.index_path / "index.faiss"
            chunks_file = self.index_path / "chunks.json"

            if all_embeddings:
                dimension = len(all_embeddings[0])
                index = faiss.IndexFlatL2(dimension)
                vectors = np.array(all_embeddings).astype('float32')
                index.add(vectors)

                faiss.write_index(index, str(index_file))
                with open(chunks_file, 'w') as f:
                    json.dump(all_chunks, f)
            else:
                # Remove index files
                if index_file.exists():
                    index_file.unlink()
                if chunks_file.exists():
                    chunks_file.unlink()

            self.metadata["chunks"] = all_chunks

        except Exception as e:
            logger.error(f"Failed to rebuild index: {e}")

    def get_status(self) -> Dict:
        """Get index status"""
        index_file = self.index_path / "index.faiss"

        total_docs = len(self.metadata["documents"])
        indexed_docs = sum(1 for d in self.metadata["documents"].values() if d["status"] == "indexed")
        pending_docs = sum(1 for d in self.metadata["documents"].values() if d["status"] == "pending")
        error_docs = sum(1 for d in self.metadata["documents"].values() if d["status"] == "error")
        
        # Count by visibility
        public_docs = sum(1 for d in self.metadata["documents"].values() if d.get("visibility", "public") == "public")
        private_docs = sum(1 for d in self.metadata["documents"].values() if d.get("visibility") == "private")

        index_size = index_file.stat().st_size if index_file.exists() else 0

        return {
            "total_documents": total_docs,
            "indexed_documents": indexed_docs,
            "pending_documents": pending_docs,
            "error_documents": error_docs,
            "public_documents": public_docs,
            "private_documents": private_docs,
            "total_chunks": len(self.metadata.get("chunks", [])),
            "index_size_bytes": index_size,
            "last_updated": self.metadata.get("last_updated")
        }


# ==================== Index Manager Cache ====================

_index_managers: Dict[str, FAISSIndexManager] = {}

def get_index_manager(config: ClientConfig) -> FAISSIndexManager:
    """Get or create index manager for tenant"""
    if config.client_id not in _index_managers:
        _index_managers[config.client_id] = FAISSIndexManager(config)
    return _index_managers[config.client_id]


# ==================== Document Endpoints ====================

@knowledge_router.get("/documents")
async def list_documents(
    category: Optional[str] = None,
    status: Optional[str] = None,
    visibility: Optional[str] = None,
    config: ClientConfig = Depends(get_client_config)
):
    """List all documents"""
    manager = get_index_manager(config)
    documents = manager.get_documents(visibility=visibility)

    # Filter
    if category:
        documents = [d for d in documents if d.category == category]
    if status:
        documents = [d for d in documents if d.status == status]

    return {
        "success": True,
        "data": [d.model_dump() for d in documents],
        "count": len(documents)
    }


@knowledge_router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    tags: str = Form(default=""),
    visibility: str = Form(default="public"),
    auto_index: bool = Form(default=True),
    config: ClientConfig = Depends(get_client_config)
):
    """Upload a document"""
    manager = get_index_manager(config)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    
    # Validate visibility
    if visibility not in ["public", "private"]:
        visibility = "public"

    # Add document
    doc = manager.add_document(file, category, tag_list, visibility)

    # Auto-index if requested
    if auto_index:
        try:
            doc = manager.index_document(doc.document_id)
        except Exception as e:
            logger.error(f"Auto-index failed: {e}")

    return {
        "success": True,
        "data": doc.model_dump()
    }


@knowledge_router.get("/documents/{document_id}")
async def get_document(
    document_id: str,
    config: ClientConfig = Depends(get_client_config)
):
    """Get document by ID"""
    manager = get_index_manager(config)
    doc = manager.get_document(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "success": True,
        "data": doc.model_dump()
    }


@knowledge_router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    config: ClientConfig = Depends(get_client_config)
):
    """Delete a document"""
    manager = get_index_manager(config)

    if not manager.delete_document(document_id):
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "success": True,
        "message": f"Document {document_id} deleted"
    }


@knowledge_router.post("/documents/{document_id}/reindex")
async def reindex_document(
    document_id: str,
    config: ClientConfig = Depends(get_client_config)
):
    """Re-index a document"""
    manager = get_index_manager(config)

    doc = manager.index_document(document_id)

    return {
        "success": True,
        "data": doc.model_dump()
    }


@knowledge_router.get("/documents/{document_id}/download")
async def download_document(
    document_id: str,
    config: ClientConfig = Depends(get_client_config)
):
    """Download original document"""
    manager = get_index_manager(config)
    doc = manager.get_document(document_id)

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_meta = manager.metadata["documents"][document_id]
    file_path = Path(doc_meta["file_path"])

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        filename=doc.filename,
        media_type="application/octet-stream"
    )


# ==================== Search Endpoint ====================

@knowledge_router.post("/search")
async def search_knowledge(
    request: SearchRequest,
    config: ClientConfig = Depends(get_client_config)
):
    """Search the knowledge base"""
    manager = get_index_manager(config)

    results = manager.search(
        query=request.query,
        top_k=request.top_k,
        category=request.category,
        visibility=request.visibility,
        min_score=request.min_score
    )

    return {
        "success": True,
        "query": request.query,
        "data": results,
        "count": len(results)
    }


@knowledge_router.get("/search")
async def search_knowledge_get(
    query: str,
    top_k: int = Query(default=5, ge=1, le=20),
    category: Optional[str] = None,
    visibility: Optional[str] = None,
    config: ClientConfig = Depends(get_client_config)
):
    """Search the knowledge base (GET method)"""
    manager = get_index_manager(config)

    results = manager.search(
        query=query,
        top_k=top_k,
        category=category,
        visibility=visibility
    )

    return {
        "success": True,
        "query": query,
        "data": results,
        "count": len(results)
    }


# ==================== Status & Admin ====================

@knowledge_router.get("/status")
async def get_index_status(
    config: ClientConfig = Depends(get_client_config)
):
    """Get knowledge base status"""
    manager = get_index_manager(config)
    status = manager.get_status()

    return {
        "success": True,
        "data": status
    }


@knowledge_router.post("/rebuild")
async def rebuild_index(
    config: ClientConfig = Depends(get_client_config)
):
    """Rebuild the entire FAISS index"""
    manager = get_index_manager(config)

    manager._rebuild_index()
    manager._save_metadata()

    status = manager.get_status()

    return {
        "success": True,
        "message": "Index rebuilt",
        "data": status
    }


@knowledge_router.get("/categories")
async def list_categories(
    config: ClientConfig = Depends(get_client_config)
):
    """List document categories"""
    manager = get_index_manager(config)
    documents = manager.get_documents()

    categories = {}
    for doc in documents:
        cat = doc.category
        if cat not in categories:
            categories[cat] = {"name": cat, "count": 0}
        categories[cat]["count"] += 1

    return {
        "success": True,
        "data": list(categories.values())
    }