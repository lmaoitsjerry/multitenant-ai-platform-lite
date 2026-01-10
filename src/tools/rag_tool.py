"""
RAG Tool - Multi-Tenant Version

Refactored to use ClientConfig for Vertex AI RAG corpus.
Supports client-specific knowledge bases.

Usage:
    from config.loader import ClientConfig  
    from src.tools.rag_tool.py import RAGTool
    
    config = ClientConfig('africastay')
    rag = RAGTool(config)
    results = rag.search_knowledge_base('visa requirements for Zanzibar')
"""

from typing import List, Optional
from dataclasses import dataclass
import logging

from google.cloud import aiplatform
from vertexai.preview import rag
from vertexai.preview.generative_models import GenerativeModel, Tool

from config.loader import ClientConfig

logger = logging.getLogger(__name__)


@dataclass
class ScoredResult:
    text: str
    source: str
    score: float
    strategy: str
    chunk_hash: str = ""


class RAGTool:
    """
    RAG Tool using Vertex AI
    Supports multi-tenant knowledge bases via ClientConfig
    """
    
    def __init__(self, config: ClientConfig):
        """
        Initialize RAG tool with client configuration
        
        Args:
            config: ClientConfig instance
        """
        self.config = config
        
        try:
            # Initialize Vertex AI
            aiplatform.init(
                project=config.gcp_project_id,
                location=config.gcp_region
            )
            
            self.corpus_id = config.corpus_id
            
            if not self.corpus_id:
                logger.warning("⚠️ No corpus_id configured - RAG search will not work")
                self.corpus_id = None
            else:
                logger.info(f"✅ RAG Tool initialized with corpus: {self.corpus_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vertex AI RAG: {e}")
            self.corpus_id = None
    
    def search_knowledge_base(
        self, 
        query: str, 
        top_k: int = 10,
        agent_type: str = "helpdesk"
    ) -> str:
        """
        Search the knowledge base using Vertex AI RAG
        
        Args:
            query: Search query
            top_k: Number of results to return
            agent_type: Type of agent ("helpdesk" or "inbound")
        
        Returns:
            Formatted string with search results
        """
        if not self.corpus_id:
            return "Knowledge base not configured for this client."
        
        try:
            logger.info(f"🔍 RAG search: '{query}' (top_k={top_k}, agent={agent_type})")
            
            # Use Vertex AI RAG retrieval
            response = rag.retrieval_query(
                rag_resources=[
                    rag.RagResource(
                        rag_corpus=f"projects/{self.config.gcp_project_id}/locations/{self.config.gcp_region}/ragCorpora/{self.corpus_id}",
                    )
                ],
                text=query,
                similarity_top_k=top_k,
            )
            
            if not response or not hasattr(response, 'contexts'):
                logger.warning(f"⚠️  No results found for: {query}")
                return "No relevant information found in the knowledge base."
            
            # Format results
            formatted_results = self._format_results(response.contexts, query)
            
            logger.info(f"✅ RAG returned {len(response.contexts)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error in search_knowledge_base: {e}")
            return f"Error searching knowledge base: {str(e)}"
    
    def _format_results(self, contexts: List, query: str) -> str:
        """Format Vertex AI RAG results into readable text"""
        
        formatted = f"Found {len(contexts)} relevant documents:\n\n"
        
        for i, context in enumerate(contexts, 1):
            # Extract content and metadata
            content = context.text if hasattr(context, 'text') else str(context)
            source = context.source_uri if hasattr(context, 'source_uri') else 'Unknown'
            
            formatted += f"--- Result {i} ---\n"
            formatted += f"Source: {source}\n"
            formatted += f"{content}\n\n"
        
        return formatted
    
    def search_with_filters(
        self,
        query: str,
        filters: Optional[dict] = None,
        top_k: int = 10
    ) -> List[dict]:
        """
        Search with optional filters
        
        Args:
            query: Search query
            filters: Optional filters (e.g., {"visibility": "public"})
            top_k: Number of results
        
        Returns:
            List of result dictionaries
        """
        try:
            # For now, basic search (filtering can be added later)
            response = rag.retrieval_query(
                rag_resources=[
                    rag.RagResource(
                        rag_corpus=f"projects/{self.config.gcp_project_id}/locations/{self.config.gcp_region}/ragCorpora/{self.corpus_id}",
                    )
                ],
                text=query,
                similarity_top_k=top_k,
            )
            
            if response and hasattr(response, 'contexts'):
                return [{'content': ctx.text, 'source': ctx.source_uri} for ctx in response.contexts]
            return []
            
        except Exception as e:
            logger.error(f"Error in filtered search: {e}")
            return []
