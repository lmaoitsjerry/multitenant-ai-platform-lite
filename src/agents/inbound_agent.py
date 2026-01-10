"""
Inbound Agent - Multi-Tenant Version with Google GenAI and RAG

Customer-facing conversational AI for travel inquiries.
Uses Google GenAI (Gemini) for natural language understanding.
Integrates with Knowledge Base (FAISS) for RAG-enhanced responses.

Usage:
    from config.loader import ClientConfig
    from src.agents.inbound_agent import InboundAgent

    config = ClientConfig('africastay')
    agent = InboundAgent(config, session_id='session123')
    response = agent.chat('I want to visit Zanzibar')
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import json

from config.loader import ClientConfig

logger = logging.getLogger(__name__)

# Try Google GenAI
GENAI_AVAILABLE = False
try:
    from google import genai
    GENAI_AVAILABLE = True
except ImportError:
    logger.warning("Google GenAI not installed. Run: pip install google-genai")


class KnowledgeBaseRAG:
    """Simple RAG interface for knowledge base queries"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.base_path = Path(f"clients/{client_id}/data/knowledge")
        self.index_path = self.base_path / "faiss_index"
        self.metadata_file = self.base_path / "metadata.json"
        self._embeddings = None
        self._index = None
        self._chunks = None
        
    def _load_index(self):
        """Load FAISS index and chunks"""
        if self._index is not None:
            return True
            
        index_file = self.index_path / "index.faiss"
        chunks_file = self.index_path / "chunks.json"
        
        if not index_file.exists() or not chunks_file.exists():
            logger.warning(f"No knowledge base index found for {self.client_id}")
            return False
            
        try:
            import faiss
            self._index = faiss.read_index(str(index_file))
            with open(chunks_file, 'r') as f:
                self._chunks = json.load(f)
            logger.info(f"Loaded knowledge base: {len(self._chunks)} chunks")
            return True
        except Exception as e:
            logger.error(f"Failed to load knowledge base: {e}")
            return False
    
    def _get_embeddings_model(self):
        """Get embeddings model"""
        if self._embeddings is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embeddings = SentenceTransformer('all-MiniLM-L6-v2')
            except ImportError:
                logger.error("sentence-transformers not installed")
                return None
        return self._embeddings
    
    def search(
        self, 
        query: str, 
        top_k: int = 3, 
        visibility: str = "public",
        min_score: float = 0.4
    ) -> List[Dict]:
        """
        Search knowledge base for relevant content
        
        Args:
            query: Search query
            top_k: Number of results to return
            visibility: Filter by visibility (public/private)
            min_score: Minimum similarity score
            
        Returns:
            List of relevant chunks with content and metadata
        """
        if not self._load_index():
            return []
            
        model = self._get_embeddings_model()
        if model is None:
            return []
            
        try:
            import numpy as np
            
            # Embed query
            query_embedding = model.encode([query], convert_to_numpy=True)
            query_vector = query_embedding.astype('float32')
            
            # Search
            distances, indices = self._index.search(query_vector, min(top_k * 3, len(self._chunks)))
            
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx < 0 or idx >= len(self._chunks):
                    continue
                    
                chunk = self._chunks[idx]
                
                # Filter by visibility - only public docs for inbound agent
                chunk_visibility = chunk.get("visibility", "public")
                if visibility and chunk_visibility != visibility:
                    continue
                
                # Convert L2 distance to similarity score
                score = 1 / (1 + dist)
                
                if score >= min_score:
                    results.append({
                        "content": chunk["content"],
                        "score": round(score, 3),
                        "document_id": chunk.get("document_id"),
                        "category": chunk.get("category")
                    })
                    
                if len(results) >= top_k:
                    break
                    
            return results
            
        except Exception as e:
            logger.error(f"Knowledge base search failed: {e}")
            return []


class InboundAgent:
    """Customer-facing conversational AI - Multi-tenant version with GenAI and RAG"""

    def __init__(self, config: ClientConfig, session_id: str):
        """
        Initialize inbound agent

        Args:
            config: ClientConfig instance
            session_id: Unique session identifier
        """
        self.config = config
        self.session_id = session_id
        self.conversation_history: List[Dict] = []
        self.collected_info: Dict[str, Any] = {}
        self.genai_client = None
        self.model_name = "gemini-2.0-flash-001"
        
        # Initialize RAG
        self.rag = KnowledgeBaseRAG(config.client_id)

        # Initialize GenAI
        if GENAI_AVAILABLE:
            try:
                self.genai_client = genai.Client(
                    vertexai=True,
                    project=config.gcp_project_id,
                    location=config.gcp_region
                )
                logger.info(f"Inbound agent initialized with GenAI for {config.client_id}")
            except Exception as e:
                logger.error(f"GenAI init failed: {e}")

        # Load system prompt
        self.system_prompt = self._build_system_prompt()

        logger.info(f"Inbound agent initialized for {config.client_id}, session: {session_id}")

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the inbound agent"""
        # Try to load from template file
        try:
            prompt_path = self.config.get_prompt_path('inbound')
            if prompt_path.exists():
                base_prompt = prompt_path.read_text()
            else:
                base_prompt = self._default_prompt()
        except Exception as e:
            logger.warning(f"Could not load inbound prompt: {e}")
            base_prompt = self._default_prompt()

        # Add dynamic context
        context = f"""

CURRENT CONTEXT:
- Company: {self.config.company_name}
- Available Destinations: {', '.join(self.config.destination_names)}
- Currency: {self.config.currency}
- Timezone: {self.config.timezone}

INFORMATION TO COLLECT:
1. Destination (required)
2. Travel dates - check-in and check-out (required)
3. Number of adults (required)
4. Number of children and their ages (if applicable)
5. Budget range (optional but helpful)
6. Special requirements (honeymoon, dietary, accessibility, etc.)
7. Hotel preferences (star rating, meal plan, specific hotels)
8. Customer name and email (required for quote)

CONVERSATION GUIDELINES:
- Be warm, friendly, and enthusiastic about travel
- Ask one or two questions at a time, don't overwhelm
- Confirm details before generating a quote
- If customer provides email, offer to send a detailed quote
- Highlight unique experiences for each destination
- Use information from the KNOWLEDGE BASE when available to provide accurate, specific details
- If you have relevant knowledge base information, use it to enrich your responses
"""
        return base_prompt + context

    def _default_prompt(self) -> str:
        """Default prompt if template not found"""
        return f"""You are a friendly and professional travel consultant for {self.config.company_name}.

Your role is to help customers plan their dream vacation to African and Indian Ocean destinations.

Be conversational, warm, and helpful. Guide customers through the booking inquiry process
while making them excited about their upcoming trip.

When you have collected enough information (destination, dates, number of travelers, email),
let them know you can prepare a personalized quote for them.

IMPORTANT: When knowledge base information is provided, use it to give accurate and specific 
answers about hotels, destinations, visa requirements, and other travel details.
"""

    def _search_knowledge_base(self, query: str) -> str:
        """
        Search knowledge base for relevant information
        
        Args:
            query: The user's question or message
            
        Returns:
            Formatted context string from knowledge base, or empty string if nothing found
        """
        results = self.rag.search(query, top_k=3, visibility="public", min_score=0.35)
        
        if not results:
            return ""
            
        context_parts = ["RELEVANT KNOWLEDGE BASE INFORMATION:"]
        for i, result in enumerate(results, 1):
            context_parts.append(f"\n[Source {i}] (relevance: {result['score']}):")
            context_parts.append(result['content'][:800])  # Limit chunk size
            
        context_parts.append("\nUse this information to provide accurate answers. If the information doesn't seem relevant to the user's question, you can ignore it.")
        
        return "\n".join(context_parts)

    def chat(
        self,
        message: str,
        customer_info: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a customer message and generate response

        Args:
            message: Customer's message
            customer_info: Optional pre-filled customer information

        Returns:
            Response dict with 'response', 'collected_info', 'ready_for_quote'
        """
        # Update collected info if provided
        if customer_info:
            self.collected_info.update(customer_info)

        # Add message to history
        self.conversation_history.append({
            'role': 'user',
            'content': message,
            'timestamp': datetime.now().isoformat()
        })

        try:
            if self.genai_client:
                response_text = self._chat_genai(message)
            else:
                response_text = "I apologize, but I'm currently unable to process your request. Please email us directly or call our team."

            # Add response to history
            self.conversation_history.append({
                'role': 'assistant',
                'content': response_text,
                'timestamp': datetime.now().isoformat()
            })

            # Extract any new information from the conversation
            self._extract_info_from_message(message)

            # Check if we have enough info for a quote
            ready_for_quote = self._check_ready_for_quote()

            return {
                'success': True,
                'response': response_text,
                'session_id': self.session_id,
                'collected_info': self.collected_info,
                'ready_for_quote': ready_for_quote
            }

        except Exception as e:
            logger.error(f"Inbound chat error: {e}")
            return {
                'success': False,
                'response': "I apologize for the inconvenience. Let me connect you with one of our consultants.",
                'session_id': self.session_id,
                'error': str(e)
            }

    def _chat_genai(self, message: str) -> str:
        """Generate response using Google GenAI with RAG"""
        # Search knowledge base for relevant context
        rag_context = self._search_knowledge_base(message)
        
        # Build conversation context
        conversation = f"{self.system_prompt}\n\n"
        
        # Add RAG context if found
        if rag_context:
            conversation += f"{rag_context}\n\n"
            logger.info(f"Added RAG context to inbound agent response")

        # Add collected info context
        if self.collected_info:
            conversation += f"Information collected so far: {self.collected_info}\n\n"

        # Add conversation history
        conversation += "Conversation:\n"
        for msg in self.conversation_history[-10:]:  # Last 10 messages
            role = "Customer" if msg['role'] == 'user' else "Consultant"
            conversation += f"{role}: {msg['content']}\n"

        conversation += "Consultant:"

        # Generate response
        response = self.genai_client.models.generate_content(
            model=self.model_name,
            contents=conversation
        )

        return response.text

    def _extract_info_from_message(self, message: str):
        """Extract travel information from customer message"""
        message_lower = message.lower()

        # Extract destination
        for dest in self.config.destination_names:
            if dest.lower() in message_lower:
                self.collected_info['destination'] = dest
                break

        # Extract number of adults
        import re
        adults_match = re.search(r'(\d+)\s*(?:adult|person|people|pax)', message_lower)
        if adults_match:
            self.collected_info['adults'] = int(adults_match.group(1))

        # Extract children
        children_match = re.search(r'(\d+)\s*(?:child|children|kid)', message_lower)
        if children_match:
            self.collected_info['children'] = int(children_match.group(1))

        # Extract email
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', message)
        if email_match:
            self.collected_info['email'] = email_match.group(0)

        # Extract name patterns like "my name is X" or "I'm X"
        name_patterns = [
            r"my name is (\w+)",
            r"i'm (\w+)",
            r"i am (\w+)",
            r"this is (\w+)",
            r"call me (\w+)"
        ]
        for pattern in name_patterns:
            name_match = re.search(pattern, message_lower)
            if name_match:
                self.collected_info['name'] = name_match.group(1).capitalize()
                break

    def _check_ready_for_quote(self) -> bool:
        """Check if we have minimum required info for a quote"""
        required = ['destination', 'email']
        return all(self.collected_info.get(field) for field in required)

    def get_collected_info(self) -> Dict[str, Any]:
        """Get all collected customer information"""
        return self.collected_info.copy()

    def set_customer_info(self, info: Dict[str, Any]):
        """Set customer information (e.g., from CRM lookup)"""
        self.collected_info.update(info)

    def get_conversation_history(self) -> List[Dict]:
        """Get conversation history"""
        return self.conversation_history.copy()

    def generate_quote_request(self) -> Optional[Dict[str, Any]]:
        """
        Generate a quote request from collected information

        Returns quote request dict if ready, None if missing required fields
        """
        if not self._check_ready_for_quote():
            return None

        return {
            'name': self.collected_info.get('name', 'Customer'),
            'email': self.collected_info['email'],
            'phone': self.collected_info.get('phone'),
            'destination': self.collected_info['destination'],
            'check_in': self.collected_info.get('check_in'),
            'check_out': self.collected_info.get('check_out'),
            'adults': self.collected_info.get('adults', 2),
            'children': self.collected_info.get('children', 0),
            'children_ages': self.collected_info.get('children_ages', []),
            'budget': self.collected_info.get('budget'),
            'message': self.collected_info.get('special_requests', ''),
            'source': 'chat',
            'session_id': self.session_id
        }
