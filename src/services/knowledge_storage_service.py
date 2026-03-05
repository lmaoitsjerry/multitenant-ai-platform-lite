"""
Knowledge Storage Service - Supabase Backend

Manages tenant knowledge documents using:
- Supabase Storage: File storage (PDFs, DOCX, etc.)
- Supabase Database: Metadata and content chunks
- PostgreSQL Full-Text Search: Content search

Replaces the filesystem-based KnowledgeIndexManager.
"""

import os
import uuid
import logging
from io import BytesIO
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

from fastapi import UploadFile, HTTPException
from pydantic import BaseModel
from src.utils.error_handling import log_and_suppress

logger = logging.getLogger(__name__)

# Storage bucket name
KNOWLEDGE_BUCKET = "knowledge-documents"


class DocumentMetadata(BaseModel):
    """Document metadata model"""
    document_id: str
    filename: str
    category: str = "general"
    tags: List[str] = []
    visibility: str = "public"
    file_type: str
    file_size: int = 0
    status: str = "pending"
    chunk_count: int = 0
    uploaded_at: Optional[str] = None
    indexed_at: Optional[str] = None
    error_message: Optional[str] = None
    storage_path: Optional[str] = None


class SupabaseKnowledgeManager:
    """
    Manages knowledge documents in Supabase.

    Storage:
    - Files stored in Supabase Storage bucket
    - Metadata stored in knowledge_documents table
    - Content chunks stored as JSONB for search
    """

    def __init__(self, config):
        """
        Initialize with client config.

        Args:
            config: ClientConfig with supabase_url and supabase_key
        """
        self.config = config
        self.tenant_id = config.client_id
        self.client = self._get_supabase_client()

    def _get_supabase_client(self):
        """Get Supabase client from config or environment"""
        try:
            from supabase import create_client

            url = getattr(self.config, 'supabase_url', None) or os.getenv("SUPABASE_URL")
            key = getattr(self.config, 'supabase_key', None) or os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

            if not url or not key:
                logger.warning("Supabase credentials not configured")
                return None

            return create_client(url, key)
        except Exception as e:
            logger.error(f"Failed to create Supabase client: {e}")
            return None

    def _ensure_bucket_exists(self):
        """Ensure the storage bucket exists"""
        if not self.client:
            return False

        try:
            # Try to get bucket info
            self.client.storage.get_bucket(KNOWLEDGE_BUCKET)
            return True
        except Exception as e:
            log_and_suppress(e, context="kb_get_bucket", bucket=KNOWLEDGE_BUCKET)
            # Try to create bucket
            try:
                self.client.storage.create_bucket(
                    KNOWLEDGE_BUCKET,
                    options={"public": False}
                )
                logger.info(f"Created storage bucket: {KNOWLEDGE_BUCKET}")
                return True
            except Exception as e:
                logger.error(f"Failed to create bucket: {e}")
                return False

    def add_document(
        self,
        file: UploadFile,
        category: str = "general",
        tags: List[str] = None,
        visibility: str = "public"
    ) -> DocumentMetadata:
        """
        Add a document to the knowledge base.

        Args:
            file: Uploaded file
            category: Document category
            tags: List of tags
            visibility: 'public' or 'private'

        Returns:
            DocumentMetadata
        """
        if not self.client:
            raise HTTPException(status_code=500, detail="Storage not configured")

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

        # Read file content
        content = file.file.read()
        file_size = len(content)

        # Storage path: tenant_id/document_id.extension
        storage_path = f"{self.tenant_id}/{document_id}.{file_type}"

        try:
            # Ensure bucket exists
            self._ensure_bucket_exists()

            # Upload to Supabase Storage
            self.client.storage.from_(KNOWLEDGE_BUCKET).upload(
                path=storage_path,
                file=content,
                file_options={"content-type": self._get_content_type(file_type)}
            )

            logger.info(f"Uploaded file to storage: {storage_path}")

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

        # Create database record
        now = datetime.utcnow().isoformat()
        record = {
            "tenant_id": self.tenant_id,
            "document_id": document_id,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            "storage_path": storage_path,
            "title": filename.rsplit('.', 1)[0],  # Filename without extension
            "category": category,
            "tags": tags or [],
            "visibility": visibility,
            "status": "pending",
            "created_at": now
        }

        try:
            result = self.client.table("knowledge_documents").insert(record).execute()

            if not result.data:
                raise HTTPException(status_code=500, detail="Failed to create document record")

            logger.info(f"Created document record: {document_id}")

            return DocumentMetadata(
                document_id=document_id,
                filename=filename,
                category=category,
                tags=tags or [],
                visibility=visibility,
                file_type=file_type,
                file_size=file_size,
                status="pending",
                chunk_count=0,
                uploaded_at=now,
                storage_path=storage_path
            )

        except HTTPException:
            raise
        except Exception as e:
            # Clean up storage on failure
            try:
                self.client.storage.from_(KNOWLEDGE_BUCKET).remove([storage_path])
            except Exception as e:
                log_and_suppress(e, context="kb_cleanup_storage_on_insert_failure", path=storage_path)
            logger.error(f"Failed to create document record: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to save document: {str(e)}")

    def index_document(self, document_id: str) -> DocumentMetadata:
        """
        Index a document for search.

        Extracts text content and stores chunks for full-text search.
        """
        if not self.client:
            raise HTTPException(status_code=500, detail="Storage not configured")

        # Get document record
        result = self.client.table("knowledge_documents")\
            .select("*")\
            .eq("document_id", document_id)\
            .eq("tenant_id", self.tenant_id)\
            .single()\
            .execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Document not found")

        doc = result.data

        try:
            # Download file from storage
            storage_path = doc["storage_path"]
            file_data = self.client.storage.from_(KNOWLEDGE_BUCKET).download(storage_path)

            # Extract text
            text = self._extract_text(file_data, doc["file_type"])

            # Chunk text
            chunks = self._chunk_text(text)

            if not chunks:
                raise ValueError("No content extracted from document")

            # Prepare chunk data for JSONB storage
            chunk_data = [
                {
                    "index": i,
                    "content": chunk,
                    "word_count": len(chunk.split())
                }
                for i, chunk in enumerate(chunks)
            ]

            # Update document with content and chunks
            now = datetime.utcnow().isoformat()
            update_result = self.client.table("knowledge_documents")\
                .update({
                    "content": text[:50000],  # Store first 50K chars for full-text search
                    "content_chunks": chunk_data,
                    "chunk_count": len(chunks),
                    "status": "indexed",
                    "indexed_at": now,
                    "error_message": None
                })\
                .eq("document_id", document_id)\
                .eq("tenant_id", self.tenant_id)\
                .execute()

            if not update_result.data:
                raise HTTPException(status_code=500, detail="Failed to update document")

            logger.info(f"Indexed document {document_id}: {len(chunks)} chunks")

            updated_doc = update_result.data[0]
            return DocumentMetadata(
                document_id=updated_doc["document_id"],
                filename=updated_doc["filename"],
                category=updated_doc["category"],
                tags=updated_doc.get("tags", []),
                visibility=updated_doc["visibility"],
                file_type=updated_doc["file_type"],
                file_size=updated_doc.get("file_size", 0),
                status="indexed",
                chunk_count=len(chunks),
                uploaded_at=updated_doc.get("created_at"),
                indexed_at=now,
                storage_path=updated_doc.get("storage_path")
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to index document {document_id}: {e}")

            # Update error status
            self.client.table("knowledge_documents")\
                .update({
                    "status": "error",
                    "error_message": str(e)
                })\
                .eq("document_id", document_id)\
                .eq("tenant_id", self.tenant_id)\
                .execute()

            raise HTTPException(status_code=500, detail=f"Failed to index document: {str(e)}")

    def search(
        self,
        query: str,
        top_k: int = 5,
        category: Optional[str] = None,
        visibility: Optional[str] = None,
        min_score: float = 0.1
    ) -> List[Dict]:
        """
        Search the knowledge base using PostgreSQL full-text search.
        """
        if not self.client:
            return []

        try:
            # Build query with filters
            q = self.client.table("knowledge_documents")\
                .select("document_id, filename, category, visibility, content, content_chunks")\
                .eq("tenant_id", self.tenant_id)\
                .eq("status", "indexed")

            if category:
                q = q.eq("category", category)

            if visibility:
                q = q.eq("visibility", visibility)

            result = q.execute()

            if not result.data:
                return []

            # Score and rank results using text matching
            query_lower = query.lower()
            query_words = set(query_lower.split())

            results = []
            for doc in result.data:
                content = doc.get("content", "")
                if not content:
                    continue

                content_lower = content.lower()
                content_words = set(content_lower.split())

                # Calculate relevance score
                intersection = query_words & content_words
                if not intersection:
                    continue

                # Keyword overlap score
                keyword_score = len(intersection) / len(query_words)

                # Exact phrase bonus
                phrase_bonus = 0.3 if query_lower in content_lower else 0

                score = min(keyword_score + phrase_bonus, 1.0)

                if score >= min_score:
                    # Find best matching chunk
                    best_chunk = ""
                    chunks = doc.get("content_chunks", [])
                    if chunks:
                        for chunk in chunks:
                            chunk_content = chunk.get("content", "")
                            if any(word in chunk_content.lower() for word in query_words):
                                best_chunk = chunk_content
                                break
                        if not best_chunk and chunks:
                            best_chunk = chunks[0].get("content", "")
                    else:
                        best_chunk = content[:500]

                    results.append({
                        "content": best_chunk,
                        "source": doc["filename"],
                        "score": round(score, 3),
                        "document_id": doc["document_id"],
                        "visibility": doc["visibility"],
                        "category": doc["category"]
                    })

            # Sort by score and return top_k
            results.sort(key=lambda x: x["score"], reverse=True)

            if results:
                logger.info(f"Knowledge search found {len(results)} results (top: {results[0]['score']:.3f})")

            return results[:top_k]

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def get_documents(self, visibility: Optional[str] = None) -> List[DocumentMetadata]:
        """Get all documents for this tenant"""
        if not self.client:
            return []

        try:
            q = self.client.table("knowledge_documents")\
                .select("*")\
                .eq("tenant_id", self.tenant_id)\
                .order("created_at", desc=True)

            if visibility:
                q = q.eq("visibility", visibility)

            result = q.execute()

            return [
                DocumentMetadata(
                    document_id=doc["document_id"],
                    filename=doc["filename"],
                    category=doc.get("category", "general"),
                    tags=doc.get("tags", []),
                    visibility=doc.get("visibility", "public"),
                    file_type=doc["file_type"],
                    file_size=doc.get("file_size", 0),
                    status=doc.get("status", "pending"),
                    chunk_count=doc.get("chunk_count", 0),
                    uploaded_at=doc.get("created_at"),
                    indexed_at=doc.get("indexed_at"),
                    error_message=doc.get("error_message"),
                    storage_path=doc.get("storage_path")
                )
                for doc in result.data
            ]

        except Exception as e:
            logger.error(f"Failed to get documents: {e}")
            return []

    def get_document(self, document_id: str) -> Optional[DocumentMetadata]:
        """Get document by ID"""
        if not self.client:
            return None

        try:
            result = self.client.table("knowledge_documents")\
                .select("*")\
                .eq("document_id", document_id)\
                .eq("tenant_id", self.tenant_id)\
                .single()\
                .execute()

            if not result.data:
                return None

            doc = result.data
            return DocumentMetadata(
                document_id=doc["document_id"],
                filename=doc["filename"],
                category=doc.get("category", "general"),
                tags=doc.get("tags", []),
                visibility=doc.get("visibility", "public"),
                file_type=doc["file_type"],
                file_size=doc.get("file_size", 0),
                status=doc.get("status", "pending"),
                chunk_count=doc.get("chunk_count", 0),
                uploaded_at=doc.get("created_at"),
                indexed_at=doc.get("indexed_at"),
                error_message=doc.get("error_message"),
                storage_path=doc.get("storage_path")
            )

        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None

    def delete_document(self, document_id: str) -> bool:
        """Delete a document"""
        if not self.client:
            return False

        try:
            # Get document first
            doc = self.get_document(document_id)
            if not doc:
                return False

            # Delete from storage
            if doc.storage_path:
                try:
                    self.client.storage.from_(KNOWLEDGE_BUCKET).remove([doc.storage_path])
                except Exception as e:
                    logger.warning(f"Failed to delete file from storage: {e}")

            # Delete from database
            self.client.table("knowledge_documents")\
                .delete()\
                .eq("document_id", document_id)\
                .eq("tenant_id", self.tenant_id)\
                .execute()

            logger.info(f"Deleted document: {document_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False

    def get_download_url(self, document_id: str, expires_in: int = 3600) -> Optional[str]:
        """Get a signed URL for downloading a document"""
        if not self.client:
            return None

        doc = self.get_document(document_id)
        if not doc or not doc.storage_path:
            return None

        try:
            result = self.client.storage.from_(KNOWLEDGE_BUCKET)\
                .create_signed_url(doc.storage_path, expires_in)

            return result.get("signedURL") or result.get("signedUrl")

        except Exception as e:
            logger.error(f"Failed to create signed URL: {e}")
            return None

    def get_file_content(self, document_id: str) -> Optional[bytes]:
        """Download file content"""
        if not self.client:
            return None

        doc = self.get_document(document_id)
        if not doc or not doc.storage_path:
            return None

        try:
            return self.client.storage.from_(KNOWLEDGE_BUCKET).download(doc.storage_path)
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return None

    def get_status(self) -> Dict:
        """Get knowledge base status"""
        if not self.client:
            return {"error": "Storage not configured"}

        try:
            result = self.client.table("knowledge_documents")\
                .select("status, visibility")\
                .eq("tenant_id", self.tenant_id)\
                .execute()

            docs = result.data or []

            return {
                "total_documents": len(docs),
                "indexed_documents": sum(1 for d in docs if d["status"] == "indexed"),
                "pending_documents": sum(1 for d in docs if d["status"] == "pending"),
                "error_documents": sum(1 for d in docs if d["status"] == "error"),
                "public_documents": sum(1 for d in docs if d.get("visibility") == "public"),
                "private_documents": sum(1 for d in docs if d.get("visibility") == "private"),
                "storage_backend": "supabase"
            }

        except Exception as e:
            logger.error(f"Failed to get status: {e}")
            return {"error": str(e)}

    # ==================== Helper Methods ====================

    def _get_content_type(self, file_type: str) -> str:
        """Get MIME type for file type"""
        types = {
            "pdf": "application/pdf",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "md": "text/markdown"
        }
        return types.get(file_type, "application/octet-stream")

    def _extract_text(self, file_data: bytes, file_type: str) -> str:
        """Extract text from document"""
        text = ""

        if file_type in ['txt', 'md']:
            text = file_data.decode('utf-8', errors='ignore')

        elif file_type == 'pdf':
            try:
                import pypdf
                from io import BytesIO
                reader = pypdf.PdfReader(BytesIO(file_data))
                text = "\n".join(page.extract_text() or "" for page in reader.pages)
            except ImportError:
                try:
                    import fitz  # PyMuPDF
                    doc = fitz.open(stream=file_data, filetype="pdf")
                    text = "\n".join(page.get_text() for page in doc)
                except ImportError:
                    raise HTTPException(status_code=500, detail="No PDF library available")

        elif file_type == 'docx':
            try:
                from docx import Document
                from io import BytesIO
                doc = Document(BytesIO(file_data))
                text = "\n".join(para.text for para in doc.paragraphs)
            except ImportError:
                raise HTTPException(status_code=500, detail="python-docx not installed")

        return text.strip()

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
        """Split text into chunks"""
        words = text.split()
        chunks = []

        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)

        return chunks


# ==================== Manager Cache ====================

_managers: Dict[str, SupabaseKnowledgeManager] = {}


def get_supabase_knowledge_manager(config) -> SupabaseKnowledgeManager:
    """Get or create knowledge manager for tenant"""
    client_id = config.client_id

    if client_id not in _managers:
        _managers[client_id] = SupabaseKnowledgeManager(config)
        logger.info(f"Created Supabase knowledge manager for tenant: {client_id}")

    return _managers[client_id]


def clear_knowledge_manager_cache():
    """Clear manager cache (for testing)"""
    _managers.clear()
