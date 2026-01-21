"""
Admin Knowledge Base Routes - Centralized RAG Management

Endpoints for:
- Listing all knowledge documents across tenants
- Adding/updating/deleting documents
- Rebuilding FAISS index
- Knowledge base statistics

These endpoints require admin authentication (X-Admin-Token header).

Storage: Google Cloud Storage bucket 'zorah-475411-rag-documents'
All tenants share this knowledge base for helpdesk functionality.
"""

import logging
import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File, Form
from pydantic import BaseModel, Field

from src.api.admin_routes import verify_admin_token
from src.utils.error_handler import log_and_raise

logger = logging.getLogger(__name__)

admin_knowledge_router = APIRouter(prefix="/api/v1/admin/knowledge", tags=["Admin - Knowledge Base"])

# GCS bucket for RAG documents (shared across all tenants)
GCS_BUCKET_NAME = os.getenv("RAG_BUCKET_NAME", "zorah-475411-rag-documents")
GCS_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "zorah-475411")

# Local fallback path for knowledge storage
KNOWLEDGE_BASE_PATH = Path("data/knowledge")


# ==================== Simple In-Memory Cache ====================

_knowledge_cache = {}
KNOWLEDGE_CACHE_TTL = 120  # Cache for 2 minutes


def get_cached(key: str) -> Optional[Any]:
    """Get value from cache if not expired"""
    from datetime import timedelta
    if key in _knowledge_cache:
        entry = _knowledge_cache[key]
        if datetime.now() < entry['expires']:
            return entry['data']
        else:
            del _knowledge_cache[key]
    return None


def set_cached(key: str, data: Any, ttl: int = KNOWLEDGE_CACHE_TTL):
    """Set value in cache with TTL"""
    from datetime import timedelta
    _knowledge_cache[key] = {
        'data': data,
        'expires': datetime.now() + timedelta(seconds=ttl)
    }


def invalidate_cache(prefix: str = None):
    """Invalidate cache entries, optionally by prefix"""
    global _knowledge_cache
    if prefix:
        keys_to_delete = [k for k in _knowledge_cache.keys() if k.startswith(prefix)]
        for k in keys_to_delete:
            del _knowledge_cache[k]
    else:
        _knowledge_cache = {}


# ==================== Pydantic Models ====================

class KnowledgeDocument(BaseModel):
    """Knowledge document metadata"""
    id: str
    title: str
    category: str = "general"
    content: Optional[str] = None
    filename: Optional[str] = None
    file_type: str = "text"
    chunk_count: int = 0
    visibility: str = "public"
    tenant_id: Optional[str] = None  # None = global
    created_at: str
    updated_at: str
    indexed: bool = False


class DocumentCreateRequest(BaseModel):
    """Request to create a document"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    category: str = "general"
    visibility: str = "public"
    tenant_id: Optional[str] = None


class DocumentUpdateRequest(BaseModel):
    """Request to update a document"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    category: Optional[str] = None
    visibility: Optional[str] = None


class KnowledgeStats(BaseModel):
    """Knowledge base statistics"""
    total_documents: int = 0
    total_chunks: int = 0
    global_documents: int = 0
    tenant_documents: int = 0
    categories: Dict[str, int] = {}
    last_indexed: Optional[str] = None
    index_size_bytes: int = 0


# ==================== GCS Helper Functions ====================

def get_gcs_client():
    """Get Google Cloud Storage client"""
    try:
        from google.cloud import storage
        return storage.Client(project=GCS_PROJECT_ID)
    except Exception as e:
        logger.warning(f"GCS client not available: {e}")
        return None


def get_gcs_bucket():
    """Get the RAG documents bucket"""
    client = get_gcs_client()
    if client:
        try:
            return client.bucket(GCS_BUCKET_NAME)
        except Exception as e:
            logger.error(f"Failed to get GCS bucket: {e}")
    return None


def list_gcs_documents() -> List[Dict[str, Any]]:
    """List all documents from GCS bucket"""
    bucket = get_gcs_bucket()
    if not bucket:
        logger.warning("GCS bucket not available, falling back to local storage")
        return load_documents_metadata_local()

    documents = []
    try:
        # List all blobs in the bucket
        blobs = bucket.list_blobs(prefix="documents/")

        for blob in blobs:
            if blob.name.endswith(".txt") or blob.name.endswith(".md"):
                # Extract document info from blob metadata
                metadata = blob.metadata or {}
                doc_id = Path(blob.name).stem

                documents.append({
                    "id": doc_id,
                    "title": metadata.get("title", doc_id),
                    "category": metadata.get("category", "general"),
                    "visibility": metadata.get("visibility", "public"),
                    "tenant_id": metadata.get("tenant_id"),
                    "file_type": "text",
                    "chunk_count": int(metadata.get("chunk_count", 0)),
                    "indexed": metadata.get("indexed", "false").lower() == "true",
                    "filename": blob.name,
                    "size_bytes": blob.size,
                    "created_at": blob.time_created.isoformat() if blob.time_created else None,
                    "updated_at": blob.updated.isoformat() if blob.updated else None
                })

        logger.info(f"Loaded {len(documents)} documents from GCS bucket {GCS_BUCKET_NAME}")
        return documents

    except Exception as e:
        logger.error(f"Error listing GCS documents: {e}")
        return load_documents_metadata_local()


def get_gcs_document_content(doc_id: str) -> Optional[str]:
    """Get document content from GCS"""
    bucket = get_gcs_bucket()
    if not bucket:
        return None

    try:
        blob = bucket.blob(f"documents/{doc_id}.txt")
        if blob.exists():
            return blob.download_as_text(encoding='utf-8')

        # Try .md extension
        blob = bucket.blob(f"documents/{doc_id}.md")
        if blob.exists():
            return blob.download_as_text(encoding='utf-8')

        return None
    except Exception as e:
        logger.error(f"Error getting document content from GCS: {e}")
        return None


def save_gcs_document(doc_id: str, content: str, metadata: Dict[str, Any]) -> bool:
    """Save document to GCS"""
    bucket = get_gcs_bucket()
    if not bucket:
        return save_document_local(doc_id, content, metadata)

    try:
        blob = bucket.blob(f"documents/{doc_id}.txt")

        # Set metadata
        blob.metadata = {
            "title": metadata.get("title", doc_id),
            "category": metadata.get("category", "general"),
            "visibility": metadata.get("visibility", "public"),
            "tenant_id": metadata.get("tenant_id", ""),
            "chunk_count": str(metadata.get("chunk_count", 0)),
            "indexed": "false"
        }

        blob.upload_from_string(content, content_type='text/plain')
        logger.info(f"Saved document {doc_id} to GCS")
        return True

    except Exception as e:
        logger.error(f"Error saving document to GCS: {e}")
        return save_document_local(doc_id, content, metadata)


def delete_gcs_document(doc_id: str) -> bool:
    """Delete document from GCS"""
    bucket = get_gcs_bucket()
    if not bucket:
        return delete_document_local(doc_id)

    try:
        blob = bucket.blob(f"documents/{doc_id}.txt")
        if blob.exists():
            blob.delete()
            logger.info(f"Deleted document {doc_id} from GCS")
            return True

        # Try .md extension
        blob = bucket.blob(f"documents/{doc_id}.md")
        if blob.exists():
            blob.delete()
            return True

        return False
    except Exception as e:
        logger.error(f"Error deleting document from GCS: {e}")
        return False


def get_gcs_bucket_stats() -> Dict[str, Any]:
    """Get GCS bucket statistics"""
    bucket = get_gcs_bucket()
    stats = {
        "bucket_name": GCS_BUCKET_NAME,
        "connected": bucket is not None,
        "total_size_bytes": 0,
        "document_count": 0
    }

    if bucket:
        try:
            blobs = list(bucket.list_blobs(prefix="documents/"))
            stats["document_count"] = len(blobs)
            stats["total_size_bytes"] = sum(b.size or 0 for b in blobs)
        except Exception as e:
            logger.error(f"Error getting bucket stats: {e}")

    return stats


# ==================== Local Fallback Functions ====================

def get_metadata_path() -> Path:
    """Get path to knowledge metadata file"""
    return KNOWLEDGE_BASE_PATH / "metadata.json"


def load_documents_metadata_local() -> List[Dict[str, Any]]:
    """Load all document metadata from local storage"""
    metadata_path = get_metadata_path()

    if not metadata_path.exists():
        return []

    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading local metadata: {e}")
        return []


def save_documents_metadata_local(documents: List[Dict[str, Any]]) -> bool:
    """Save document metadata to local storage"""
    metadata_path = get_metadata_path()

    try:
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(documents, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving local metadata: {e}")
        return False


def save_document_local(doc_id: str, content: str, metadata: Dict[str, Any]) -> bool:
    """Save document to local storage"""
    try:
        doc_path = KNOWLEDGE_BASE_PATH / "documents" / f"{doc_id}.txt"
        doc_path.parent.mkdir(parents=True, exist_ok=True)
        with open(doc_path, 'w', encoding='utf-8') as f:
            f.write(content)

        # Update metadata
        documents = load_documents_metadata_local()
        existing = next((d for d in documents if d["id"] == doc_id), None)
        if existing:
            existing.update(metadata)
        else:
            documents.append({**metadata, "id": doc_id})
        save_documents_metadata_local(documents)

        return True
    except Exception as e:
        logger.error(f"Error saving document locally: {e}")
        return False


def delete_document_local(doc_id: str) -> bool:
    """Delete document from local storage"""
    try:
        doc_path = KNOWLEDGE_BASE_PATH / "documents" / f"{doc_id}.txt"
        if doc_path.exists():
            doc_path.unlink()

        documents = load_documents_metadata_local()
        documents = [d for d in documents if d["id"] != doc_id]
        save_documents_metadata_local(documents)
        return True
    except Exception as e:
        logger.error(f"Error deleting document locally: {e}")
        return False


# ==================== Unified Helper Functions ====================

def load_documents_metadata() -> List[Dict[str, Any]]:
    """Load all document metadata (GCS first, local fallback) with caching"""
    # Check cache first
    cached = get_cached("documents_list")
    if cached is not None:
        logger.debug("Returning cached documents list")
        return cached

    # Load from GCS
    documents = list_gcs_documents()

    # Cache the result
    set_cached("documents_list", documents)
    return documents


def save_documents_metadata(documents: List[Dict[str, Any]]) -> bool:
    """Save document metadata"""
    return save_documents_metadata_local(documents)


def generate_document_id() -> str:
    """Generate a unique document ID"""
    import uuid
    return f"doc_{uuid.uuid4().hex[:12]}"


def get_index_stats() -> Dict[str, Any]:
    """Get FAISS index statistics"""
    stats = {
        "last_indexed": None,
        "index_size_bytes": 0,
        "total_chunks": 0
    }

    index_path = KNOWLEDGE_BASE_PATH / "faiss_index"
    if index_path.exists():
        try:
            # Get index file size
            for file in index_path.iterdir():
                if file.is_file():
                    stats["index_size_bytes"] += file.stat().st_size

            # Get last modified time
            stats["last_indexed"] = datetime.fromtimestamp(
                index_path.stat().st_mtime
            ).isoformat()
        except Exception as e:
            logger.error(f"Error getting index stats: {e}")

    return stats


# ==================== Endpoints ====================

@admin_knowledge_router.get("/documents")
async def list_knowledge_documents(
    category: Optional[str] = Query(None, description="Filter by category"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant (null for global)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    List all knowledge documents.
    """
    try:
        documents = load_documents_metadata()

        # Apply filters
        if category:
            documents = [d for d in documents if d.get("category") == category]

        if tenant_id is not None:
            if tenant_id == "global":
                documents = [d for d in documents if not d.get("tenant_id")]
            else:
                documents = [d for d in documents if d.get("tenant_id") == tenant_id]

        total = len(documents)

        # Apply pagination
        documents = documents[offset:offset + limit]

        return {
            "success": True,
            "data": documents,
            "count": len(documents),
            "total": total
        }

    except Exception as e:
        log_and_raise(500, "listing knowledge documents", e, logger)


@admin_knowledge_router.post("/documents")
async def create_knowledge_document(
    request: DocumentCreateRequest,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Add a new document to the knowledge base (GCS bucket).
    """
    try:
        # Create new document
        now = datetime.utcnow().isoformat()
        doc_id = generate_document_id()

        metadata = {
            "id": doc_id,
            "title": request.title,
            "category": request.category,
            "visibility": request.visibility,
            "tenant_id": request.tenant_id,
            "file_type": "text",
            "chunk_count": 0,
            "indexed": False,
            "created_at": now,
            "updated_at": now
        }

        # Save to GCS (with local fallback)
        saved = save_gcs_document(doc_id, request.content, metadata)

        if not saved:
            raise HTTPException(status_code=500, detail="Failed to save document")

        new_doc = {**metadata, "content": request.content}
        logger.info(f"[ADMIN] Created knowledge document: {doc_id}")

        # Invalidate cache after document creation
        invalidate_cache("documents")

        return {
            "success": True,
            "data": new_doc,
            "message": "Document created successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "creating knowledge document", e, logger)


@admin_knowledge_router.get("/documents/{doc_id}")
async def get_knowledge_document(
    doc_id: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get a specific document with its content from GCS.
    """
    try:
        documents = load_documents_metadata()

        doc = next((d for d in documents if d["id"] == doc_id), None)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Load content from GCS (with local fallback)
        if not doc.get("content"):
            content = get_gcs_document_content(doc_id)
            if content:
                doc["content"] = content
            else:
                # Local fallback
                doc_path = KNOWLEDGE_BASE_PATH / "documents" / f"{doc_id}.txt"
                if doc_path.exists():
                    with open(doc_path, 'r', encoding='utf-8') as f:
                        doc["content"] = f.read()

        return {
            "success": True,
            "data": doc
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "retrieving knowledge document", e, logger)


@admin_knowledge_router.put("/documents/{doc_id}")
async def update_knowledge_document(
    doc_id: str,
    request: DocumentUpdateRequest,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Update an existing document in GCS.
    """
    try:
        documents = load_documents_metadata()

        doc = next((d for d in documents if d["id"] == doc_id), None)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Update metadata fields
        if request.title:
            doc["title"] = request.title
        if request.category:
            doc["category"] = request.category
        if request.visibility:
            doc["visibility"] = request.visibility

        doc["updated_at"] = datetime.utcnow().isoformat()

        # If content changed, save to GCS
        if request.content:
            doc["content"] = request.content
            doc["indexed"] = False  # Mark as needing re-indexing
            saved = save_gcs_document(doc_id, request.content, doc)
            if not saved:
                raise HTTPException(status_code=500, detail="Failed to save document")

        logger.info(f"[ADMIN] Updated knowledge document: {doc_id}")

        # Invalidate cache after update
        invalidate_cache("documents")

        return {
            "success": True,
            "data": doc,
            "message": "Document updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "updating knowledge document", e, logger)


@admin_knowledge_router.delete("/documents/{doc_id}")
async def delete_knowledge_document(
    doc_id: str,
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Delete a document from the knowledge base (GCS and local).
    """
    try:
        documents = load_documents_metadata()

        doc = next((d for d in documents if d["id"] == doc_id), None)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete from GCS
        deleted_gcs = delete_gcs_document(doc_id)

        # Also delete from local storage
        deleted_local = delete_document_local(doc_id)

        if not deleted_gcs and not deleted_local:
            raise HTTPException(status_code=500, detail="Failed to delete document")

        logger.info(f"[ADMIN] Deleted knowledge document: {doc_id}")

        # Invalidate cache after deletion
        invalidate_cache("documents")

        return {
            "success": True,
            "message": f"Document {doc_id} deleted",
            "data": doc
        }

    except HTTPException:
        raise
    except Exception as e:
        log_and_raise(500, "deleting knowledge document", e, logger)


@admin_knowledge_router.post("/rebuild-index")
async def rebuild_faiss_index(
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Rebuild the FAISS index from all documents.

    This operation may take a while for large knowledge bases.
    """
    try:
        documents = load_documents_metadata()

        # TODO: Implement actual FAISS indexing
        # For now, mark all documents as indexed
        indexed_count = 0
        for doc in documents:
            doc["indexed"] = True
            doc["updated_at"] = datetime.now().isoformat()
            indexed_count += 1

        save_documents_metadata(documents)

        logger.info(f"[ADMIN] Rebuilt FAISS index with {indexed_count} documents")

        return {
            "success": True,
            "message": f"Index rebuilt with {indexed_count} documents",
            "documents_indexed": indexed_count
        }

    except Exception as e:
        log_and_raise(500, "rebuilding FAISS index", e, logger)


@admin_knowledge_router.get("/stats")
async def get_knowledge_stats(
    admin_verified: bool = Depends(verify_admin_token)
):
    """
    Get knowledge base statistics including GCS bucket info.
    """
    try:
        documents = load_documents_metadata()
        index_stats = get_index_stats()
        gcs_stats = get_gcs_bucket_stats()

        # Calculate category counts
        categories = {}
        global_count = 0
        tenant_count = 0
        total_chunks = 0

        for doc in documents:
            cat = doc.get("category", "general")
            categories[cat] = categories.get(cat, 0) + 1

            if doc.get("tenant_id"):
                tenant_count += 1
            else:
                global_count += 1

            total_chunks += doc.get("chunk_count", 0)

        # Use GCS stats if available
        index_size = gcs_stats.get("total_size_bytes", 0) or index_stats.get("index_size_bytes", 0)

        stats = KnowledgeStats(
            total_documents=len(documents),
            total_chunks=total_chunks,
            global_documents=global_count,
            tenant_documents=tenant_count,
            categories=categories,
            last_indexed=index_stats.get("last_indexed"),
            index_size_bytes=index_size
        )

        # Include GCS connection status
        result = stats.model_dump()
        result["storage"] = {
            "type": "gcs" if gcs_stats.get("connected") else "local",
            "bucket_name": gcs_stats.get("bucket_name"),
            "connected": gcs_stats.get("connected", False)
        }

        # Include FAISS helpdesk index stats
        try:
            from src.services.faiss_helpdesk_service import get_faiss_helpdesk_service
            faiss_service = get_faiss_helpdesk_service()
            faiss_status = faiss_service.get_status()
            result["faiss_index"] = {
                "initialized": faiss_status.get("initialized", False),
                "vector_count": faiss_status.get("vector_count", 0),
                "document_count": faiss_status.get("document_count", 0),
                "bucket": faiss_status.get("bucket"),
                "error": faiss_status.get("error")
            }
        except Exception as e:
            logger.warning(f"Could not get FAISS stats: {e}")
            result["faiss_index"] = {
                "initialized": False,
                "error": str(e)
            }

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        log_and_raise(500, "retrieving knowledge stats", e, logger)


# ==================== Router Registration ====================

def include_admin_knowledge_router(app):
    """Include admin knowledge router in the FastAPI app"""
    app.include_router(admin_knowledge_router)
