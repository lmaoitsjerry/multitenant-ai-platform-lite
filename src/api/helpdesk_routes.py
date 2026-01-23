"""
Helpdesk API Routes - Internal Support (Lite Version)

Provides AI-powered helpdesk support for travel agents.
Connects to local FAISS knowledge base for contextual answers.
Falls back to helpful static responses when no knowledge base results.

Key features:
- Query classification for optimized search and responses
- MMR (Maximal Marginal Relevance) for diverse hotel options
- Re-ranking for improved relevance
- Natural conversational responses via GPT-4o-mini
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from config.loader import ClientConfig
from src.middleware.auth_middleware import get_current_user_optional
from src.services.rag_response_service import generate_rag_response, get_rag_service
from src.services.query_classifier import get_query_classifier, QueryType
from src.services.reranker_service import get_reranker

logger = logging.getLogger(__name__)

helpdesk_router = APIRouter(prefix="/api/v1/helpdesk", tags=["Helpdesk"])


# ============================================================
# CLIENT CONFIG HELPER
# ============================================================

_client_configs = {}

def get_client_config(x_client_id: str = Header(None, alias="X-Client-ID")) -> ClientConfig:
    """Get client configuration from header"""
    client_id = x_client_id or os.getenv("CLIENT_ID", "example")

    if client_id not in _client_configs:
        try:
            _client_configs[client_id] = ClientConfig(client_id)
        except Exception as e:
            logger.warning(f"Could not load config for {client_id}: {e}")
            return None

    return _client_configs[client_id]


# ============================================================
# PYDANTIC MODELS
# ============================================================

class AskQuestion(BaseModel):
    question: str


class HelpdeskResponse(BaseModel):
    success: bool
    answer: Optional[str] = None
    sources: Optional[List[Dict[str, str]]] = None


# ============================================================
# HELPDESK TOPICS
# ============================================================

HELPDESK_TOPICS = [
    {
        "id": "quotes",
        "name": "Quotes & Pricing",
        "description": "Help with creating and managing travel quotes",
        "icon": "document"
    },
    {
        "id": "invoices",
        "name": "Invoices & Billing",
        "description": "Invoice generation and payment tracking",
        "icon": "currency"
    },
    {
        "id": "clients",
        "name": "Client Management",
        "description": "Managing client information and relationships",
        "icon": "users"
    },
    {
        "id": "hotels",
        "name": "Hotels & Rates",
        "description": "Hotel search, availability, and pricing",
        "icon": "building"
    },
    {
        "id": "system",
        "name": "System & Settings",
        "description": "Platform configuration and troubleshooting",
        "icon": "cog"
    }
]


# ============================================================
# STATIC HELP RESPONSES (Natural & Conversational)
# ============================================================

HELP_RESPONSES = {
    "quote_create": """Easy! Here's how to create a quote:

Head to **Quotes** in the sidebar and click **Generate Quote**. Fill in your client's details, pick the hotels and dates that work for them, and hit generate. Takes about 2 minutes once you get the hang of it.

The quote saves automatically, and you can email it straight to your client or grab the PDF. Need help with a specific step?""",

    "quote_send": """Sending a quote is quick:

Go to **Quotes**, find the one you want, and click to open it. You'll see a **Send Quote** button - just check the email address, add a personal note if you'd like, and hit send.

Your client gets a professional email with the PDF attached. They can view it right in their browser or download it.""",

    "invoice": """Sure! You can create an invoice two ways:

**From an existing quote:** Open the quote and click **Convert to Invoice** - pulls in all the details automatically.

**From scratch:** Go to **Invoices** → **Create Invoice**, add your line items and due date, and you're set.

Once it's created, you can send it to your client and track when they've viewed or paid it.""",

    "client_add": """Adding a client is straightforward:

Go to **CRM** → **All Clients** and click **Add Client**. Fill in their name, email, and phone, pick how they found you, and save.

From there you can create quotes for them, track their pipeline status, and keep all your notes in one place. Anything specific you're trying to set up?""",

    "pipeline": """The Pipeline is your visual sales tracker - a bird's-eye view of where all your clients are:

**Quoted** → They've got a quote
**Negotiating** → Working out the details
**Booked** → Trip confirmed!
**Paid** → Payment received
**Travelled** → On their trip or just got back
**Lost** → Didn't work out this time

Just drag and drop clients between stages to update their status. Super handy for keeping track of everything!""",

    "hotel": """For hotel info, head to **Pricing Guide** → **Hotels**. You can search and filter by location, star rating, or amenities.

Click any hotel to see full details and current rates. When you're building a quote, you can add hotels directly from this list - rates update automatically based on travel dates.

Looking for something specific? I can help you narrow it down.""",

    "pricing": """All your pricing lives in **Pricing Guide**:

**Rates** - View and update pricing by date range
**Hotels** - Browse properties and their rate structures

Any changes show up automatically in new quotes. You can also import rates from spreadsheets if you've got bulk updates to make.""",

    "settings": """Everything's in **Settings**:

**Profile** - Your personal details
**Company** - Business info, banking for invoices
**Branding** - Logo, colors, theme
**Notifications** - Email preferences
**Integrations** - Connected services

Most changes save automatically, but watch for the Save button when editing. Anything specific you want to set up?""",

    "default": """Hey! I'm Zara, your Zorah Travel assistant. I'm here to help you get the most out of the platform.

**I can help with:**
- **Quotes** - Creating, sending, and managing travel quotes
- **CRM** - Adding clients and tracking your pipeline
- **Invoices** - Generating and tracking payments
- **Hotels & Rates** - Finding properties and pricing
- **Settings** - Customizing your platform

Just ask me anything - like "How do I create a quote?" or "What are the pipeline stages?" and I'll walk you through it!"""
}


# ============================================================
# KNOWLEDGE BASE SEARCH HELPER
# ============================================================

def search_shared_faiss_index(
    query: str,
    top_k: int = 8,
    use_mmr: bool = False,
    lambda_mmr: float = 0.7,
    fetch_k: int = 15,
    use_rerank: bool = False
) -> List[Dict[str, Any]]:
    """
    Search the shared FAISS helpdesk index (stored in GCS).
    This is the primary knowledge base for helpdesk queries.

    Uses search_with_context for better RAG context:
    - Returns 5-8 documents (top_k=8)
    - Filters by relevance (min_score=0.3)
    - Ensures minimum 3 results for context
    - Optional MMR for diverse results (great for hotel queries)
    - Optional re-ranking for improved relevance
    """
    try:
        from src.services.faiss_helpdesk_service import get_faiss_helpdesk_service

        service = get_faiss_helpdesk_service()

        # Search with context, optionally using MMR for diversity
        results = service.search_with_context(
            query,
            top_k=top_k if not use_rerank else top_k * 2,  # Fetch more for reranking
            min_score=0.3,
            use_mmr=use_mmr,
            lambda_mmr=lambda_mmr,
            fetch_k=fetch_k
        )

        if results and use_rerank:
            # Apply re-ranking for improved relevance
            reranker = get_reranker()
            if reranker.is_available():
                results = reranker.rerank(query, results, top_k=top_k)
                logger.info(f"Re-ranked to top {len(results)} results")

        if results:
            logger.info(f"Shared FAISS search returned {len(results)} results (mmr={use_mmr}, rerank={use_rerank})")
            return results

    except Exception as e:
        logger.warning(f"Shared FAISS search failed: {e}")

    return []


def search_knowledge_base(
    config: ClientConfig,
    query: str,
    top_k: int = 5,
    use_mmr: bool = False,
    lambda_mmr: float = 0.7,
    fetch_k: int = 15,
    use_rerank: bool = False
):
    """
    Search knowledge bases for relevant content.

    Priority:
    1. Shared FAISS helpdesk index (GCS bucket: zorah-faiss-index)
       - Uses search_with_context (8 docs, min_score 0.3)
       - Optional MMR for diverse results
       - Optional re-ranking for improved relevance
    2. Per-tenant local FAISS index (fallback)
    """
    # First try the shared FAISS index with enhanced search
    shared_results = search_shared_faiss_index(
        query,
        top_k=top_k,
        use_mmr=use_mmr,
        lambda_mmr=lambda_mmr,
        fetch_k=fetch_k,
        use_rerank=use_rerank
    )
    if shared_results:
        return shared_results

    # Fall back to per-tenant index if no shared results
    if not config:
        return []

    try:
        from src.api.knowledge_routes import get_index_manager

        manager = get_index_manager(config)
        results = manager.search(
            query=query,
            top_k=top_k,
            visibility="private",
            min_score=0.4
        )

        if not results:
            results = manager.search(
                query=query,
                top_k=top_k,
                min_score=0.4
            )

        return results

    except Exception as e:
        logger.debug(f"Per-tenant knowledge base search failed: {e}")
        return []


def format_knowledge_response(results: List[Dict], question: str, query_type: str = "general") -> Dict[str, Any]:
    """
    Format knowledge base results using RAG synthesis.
    Returns dict with 'answer', 'sources', 'method'.

    Args:
        results: Search results from knowledge base
        question: User's question
        query_type: Type of query for optimized prompts (hotel_info, pricing, etc.)
    """
    return generate_rag_response(question, results, query_type)


def get_smart_response(question: str) -> tuple:
    """
    Smart keyword matching with improved logic for natural responses.
    Returns (answer, topic, sources).
    """
    q = question.lower()

    # Quote creation
    if "quote" in q and any(word in q for word in ["create", "new", "make", "generate", "how"]):
        return HELP_RESPONSES["quote_create"], "quotes", [{"topic": "Creating Quotes", "type": "guide"}]

    # Quote sending
    if "quote" in q and any(word in q for word in ["send", "email", "share"]):
        return HELP_RESPONSES["quote_send"], "quotes", [{"topic": "Sending Quotes", "type": "guide"}]

    # General quote questions
    if "quote" in q:
        return HELP_RESPONSES["quote_create"], "quotes", [{"topic": "Quotes", "type": "guide"}]

    # Invoice
    if any(word in q for word in ["invoice", "bill", "billing"]):
        return HELP_RESPONSES["invoice"], "invoices", [{"topic": "Invoices", "type": "guide"}]

    # Payment (likely invoice related)
    if "payment" in q or "pay" in q:
        return HELP_RESPONSES["invoice"], "invoices", [{"topic": "Payments & Invoices", "type": "guide"}]

    # Client/Customer add
    if any(word in q for word in ["client", "customer", "contact"]) and any(word in q for word in ["add", "new", "create"]):
        return HELP_RESPONSES["client_add"], "clients", [{"topic": "Adding Clients", "type": "guide"}]

    # Pipeline stages
    if "pipeline" in q or "stage" in q or "status" in q:
        return HELP_RESPONSES["pipeline"], "pipeline", [{"topic": "Sales Pipeline", "type": "guide"}]

    # CRM general
    if "crm" in q:
        return HELP_RESPONSES["pipeline"], "crm", [{"topic": "CRM Overview", "type": "guide"}]

    # Hotels
    if any(word in q for word in ["hotel", "accommodation", "property", "room"]):
        return HELP_RESPONSES["hotel"], "hotels", [{"topic": "Hotels & Properties", "type": "guide"}]

    # Pricing/Rates
    if any(word in q for word in ["rate", "pricing", "price", "cost"]) and "quote" not in q:
        return HELP_RESPONSES["pricing"], "pricing", [{"topic": "Pricing Management", "type": "guide"}]

    # Settings/Configuration
    if any(word in q for word in ["setting", "config", "setup", "brand", "logo", "theme", "color"]):
        return HELP_RESPONSES["settings"], "settings", [{"topic": "Settings", "type": "guide"}]

    # Default
    return HELP_RESPONSES["default"], "general", []


# ============================================================
# ENDPOINTS
# ============================================================

@helpdesk_router.post("/ask")
async def ask_helpdesk(
    request: AskQuestion,
    user: Optional[dict] = Depends(get_current_user_optional),
    config: ClientConfig = Depends(get_client_config)
):
    """
    Ask a question to the helpdesk assistant.
    Searches knowledge base first, falls back to smart static responses.

    Features:
    - Query classification for optimized search parameters
    - MMR (Maximal Marginal Relevance) for diverse hotel options
    - Re-ranking for improved relevance
    - Natural conversational responses via GPT-4o-mini

    Note: Authentication is optional - helpdesk works for all users.
    Returns timing data for performance monitoring.
    """
    start_time = time.time()

    try:
        question = request.question

        # Step 1: Classify query to determine optimal search strategy
        classifier = get_query_classifier()
        query_type, confidence = classifier.classify(question)
        search_params = classifier.get_search_params(query_type)

        logger.info(f"Query classified as {query_type.value} (confidence: {confidence:.2f})")

        # Step 2: Search with optimized parameters
        search_start = time.time()
        kb_results = search_knowledge_base(
            config,
            question,
            top_k=search_params.get('k', 5),
            use_mmr=search_params.get('use_mmr', False),
            lambda_mmr=search_params.get('lambda_mmr', 0.7),
            fetch_k=search_params.get('fetch_k', 15),
            use_rerank=search_params.get('use_rerank', False)
        )
        search_time = time.time() - search_start

        if kb_results:
            # Step 3: RAG synthesis with query type-specific prompts
            synth_start = time.time()
            rag_response = format_knowledge_response(kb_results, question, query_type.value)
            synth_time = time.time() - synth_start

            total_time = time.time() - start_time
            logger.info(f"Helpdesk RAG: search={search_time:.2f}s, synth={synth_time:.2f}s, total={total_time:.2f}s")

            if total_time > 3.0:
                logger.warning(f"Helpdesk response exceeded 3s target: {total_time:.2f}s")

            return {
                "success": True,
                "answer": rag_response['answer'],
                "sources": [
                    {
                        "filename": s.get("filename", "Knowledge Base"),
                        "score": s.get("score", 0),
                        "type": "knowledge_base"
                    }
                    for s in rag_response.get('sources', [])
                ],
                "method": rag_response.get('method', 'rag'),
                "query_type": query_type.value,
                "timing": {
                    "search_ms": int(search_time * 1000),
                    "synthesis_ms": int(synth_time * 1000),
                    "total_ms": int(total_time * 1000)
                }
            }

        # Step 4: Fall back to smart static responses
        answer, topic, sources = get_smart_response(question)
        total_time = time.time() - start_time
        logger.info(f"Helpdesk fallback: search={search_time:.2f}s, total={total_time:.2f}s (no KB results)")

        return {
            "success": True,
            "answer": answer,
            "sources": sources,
            "method": "static",
            "query_type": query_type.value,
            "timing": {
                "search_ms": int(search_time * 1000),
                "synthesis_ms": 0,
                "total_ms": int(total_time * 1000)
            }
        }

    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Helpdesk error after {total_time:.2f}s: {e}", exc_info=True)
        return {
            "success": False,
            "answer": "Oops, hit a small snag there! Could you try asking that a different way? If it keeps happening, our support team can help sort it out.",
            "sources": [],
            "timing": {
                "search_ms": 0,
                "synthesis_ms": 0,
                "total_ms": int(total_time * 1000)
            }
        }


@helpdesk_router.get("/topics")
async def get_helpdesk_topics(
    user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Get available helpdesk topics/categories.
    """
    return {
        "success": True,
        "topics": HELPDESK_TOPICS
    }


@helpdesk_router.get("/search")
async def search_helpdesk(
    q: str = "",
    user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Search help articles by keyword.
    Returns matching topics based on the search query.
    """
    if not q:
        return {"success": True, "results": HELPDESK_TOPICS}

    query = q.lower()
    results = []

    for topic in HELPDESK_TOPICS:
        if (query in topic["name"].lower() or
            query in topic["description"].lower() or
            query in topic["id"]):
            results.append(topic)

    return {
        "success": True,
        "results": results if results else HELPDESK_TOPICS[:3]
    }


@helpdesk_router.get("/faiss-status")
async def get_faiss_status() -> Dict[str, Any]:
    """
    Get status of the shared FAISS helpdesk index.
    Useful for debugging and monitoring.
    """
    try:
        from src.services.faiss_helpdesk_service import get_faiss_helpdesk_service
        service = get_faiss_helpdesk_service()
        return {
            "success": True,
            "data": service.get_status()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@helpdesk_router.get("/test-search")
async def test_faiss_search(q: str = "Maldives hotels"):
    """
    Test endpoint for FAISS search (no auth required).
    For debugging and verification only.

    Returns 5-8 documents with relevance filtering (via search_with_context).
    Also includes a RAG synthesis preview of the response.
    """
    try:
        results = search_shared_faiss_index(q)

        if results:
            # Also show RAG synthesis preview
            rag_result = generate_rag_response(q, results[:3])

            return {
                "success": True,
                "query": q,
                "results_count": len(results),
                "results": [
                    {
                        "content_preview": r.get("content", "")[:300] + "..." if len(r.get("content", "")) > 300 else r.get("content", ""),
                        "score": r.get("score"),
                        "source": r.get("source")
                    }
                    for r in results
                ],
                "synthesized_preview": rag_result['answer'][:300] + "..." if len(rag_result['answer']) > 300 else rag_result['answer'],
                "synthesis_method": rag_result.get('method', 'unknown')
            }
        else:
            return {
                "success": True,
                "query": q,
                "results_count": 0,
                "message": "No results found in FAISS index"
            }

    except Exception as e:
        logger.error(f"Test search failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@helpdesk_router.get("/health")
async def helpdesk_health() -> Dict[str, Any]:
    """
    Health check endpoint for the helpdesk RAG system.

    Verifies all components are working:
    - FAISS index is loaded and has vectors
    - OpenAI API key is configured
    - RAG synthesis is available

    Returns:
        - status: "healthy" if all checks pass, "degraded" if some fail
        - mode: "full_rag" if LLM available, "fallback_only" otherwise
        - checks: Individual component status
    """
    try:
        from src.services.faiss_helpdesk_service import get_faiss_helpdesk_service

        # Get FAISS status
        faiss_service = get_faiss_helpdesk_service()
        faiss_status = faiss_service.get_status()

        # Get RAG service status
        rag_service = get_rag_service()
        rag_status = rag_service.get_status()

        # Get reranker status
        reranker = get_reranker()
        reranker_status = reranker.get_status()

        # Determine overall health
        checks = {
            "faiss_initialized": faiss_status.get("initialized", False),
            "faiss_vector_count": faiss_status.get("vector_count", 0),
            "faiss_document_count": faiss_status.get("document_count", 0),
            "openai_api_key_configured": rag_status.get("api_key_configured", False),
            "openai_api_key_valid": rag_status.get("api_key_valid", False),
            "rag_synthesis_available": rag_status.get("synthesis_available", False),
            "reranker_available": reranker_status.get("available", False),
        }

        # Health is "healthy" if core components work
        all_healthy = all([
            checks["faiss_initialized"],
            checks["faiss_vector_count"] > 0,
            checks["openai_api_key_configured"],
            checks["rag_synthesis_available"]
        ])

        return {
            "status": "healthy" if all_healthy else "degraded",
            "mode": rag_status.get("mode", "unknown"),
            "checks": checks,
            "details": {
                "faiss": faiss_status,
                "rag": rag_status,
                "reranker": reranker_status
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "checks": {}
        }


# ============================================================
# AI AGENT ENDPOINT
# ============================================================

@helpdesk_router.post("/agent/chat")
async def agent_chat(
    request: AskQuestion,
    user: Optional[dict] = Depends(get_current_user_optional),
    config: ClientConfig = Depends(get_client_config)
):
    """
    Chat with the AI helpdesk agent (Zara).

    The agent uses OpenAI function calling to intelligently:
    - Search the knowledge base for travel info
    - Help start quote generation
    - Answer platform questions
    - Route to human support when needed

    This is a more advanced alternative to /ask that maintains
    conversation context and can take multi-step actions.
    """
    start_time = time.time()

    try:
        from src.agents.helpdesk_agent import get_helpdesk_agent

        agent = get_helpdesk_agent(config)
        result = agent.chat(request.question)

        elapsed = time.time() - start_time

        return {
            "success": True,
            "answer": result.get("response", ""),
            "tool_used": result.get("tool_used"),
            "sources": result.get("sources", []),
            "method": "agent" if result.get("tool_used") else "direct",
            "timing_ms": int(elapsed * 1000)
        }

    except Exception as e:
        logger.error(f"Agent chat failed: {e}", exc_info=True)
        return {
            "success": False,
            "answer": "Oops, hit a small snag! Could you try that again?",
            "sources": [],
            "timing_ms": int((time.time() - start_time) * 1000)
        }


@helpdesk_router.post("/agent/reset")
async def agent_reset() -> Dict[str, Any]:
    """Reset the agent's conversation history for a new session."""
    try:
        from src.agents.helpdesk_agent import get_helpdesk_agent
        agent = get_helpdesk_agent()
        agent.reset_conversation()
        return {"success": True, "message": "Conversation reset"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@helpdesk_router.get("/agent/stats")
async def agent_stats() -> Dict[str, Any]:
    """Get agent statistics."""
    try:
        from src.agents.helpdesk_agent import get_helpdesk_agent
        agent = get_helpdesk_agent()
        return {"success": True, "stats": agent.get_stats()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@helpdesk_router.post("/reinit")
async def reinit_faiss_service(clear_cache: bool = False):
    """
    Reinitialize the FAISS service to pick up new bucket configuration.

    Args:
        clear_cache: If True, delete cached index files to force re-download from GCS

    Use this after changing FAISS_BUCKET_NAME or FAISS_INDEX_PREFIX environment variables,
    or to refresh the index from a new bucket.
    """
    try:
        from src.services.faiss_helpdesk_service import (
            get_faiss_helpdesk_service,
            reset_faiss_service,
            GCS_BUCKET_NAME,
            GCS_INDEX_PREFIX
        )

        # Reset and reinitialize
        reset_faiss_service(clear_cache=clear_cache)

        # Get fresh service and initialize
        service = get_faiss_helpdesk_service()
        success = service.initialize()

        status = service.get_status()

        return {
            "success": success,
            "message": "FAISS service reinitialized" if success else "Reinitialization failed",
            "cache_cleared": clear_cache,
            "bucket": GCS_BUCKET_NAME,
            "index_prefix": GCS_INDEX_PREFIX,
            "status": status
        }

    except Exception as e:
        logger.error(f"FAISS reinit failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


# ============================================================
# ACCURACY TESTING
# ============================================================

# Test cases for accuracy validation
# Each case has a question, expected keywords, and quality criteria
ACCURACY_TEST_CASES = [
    # Hotel Information Tests
    {
        "id": "hotel_mauritius_luxury",
        "question": "What luxury hotels do you have in Mauritius?",
        "query_type": "hotel_info",
        "expected_keywords": ["mauritius", "hotel", "resort", "luxury", "5-star", "beach"],
        "must_not_contain": ["I don't know", "I'm not sure", "no information"],
        "criteria": "Should mention specific hotel names with features"
    },
    {
        "id": "hotel_maldives_honeymoon",
        "question": "Best honeymoon resorts in the Maldives?",
        "query_type": "hotel_info",
        "expected_keywords": ["maldives", "resort", "honeymoon", "romantic", "overwater", "villa"],
        "must_not_contain": ["I don't know", "I'm not sure"],
        "criteria": "Should recommend romantic properties with specifics"
    },
    {
        "id": "hotel_zanzibar_budget",
        "question": "Any affordable options in Zanzibar?",
        "query_type": "hotel_info",
        "expected_keywords": ["zanzibar", "budget", "affordable"],
        "must_not_contain": [],
        "criteria": "Should list budget-friendly options or explain pricing"
    },
    # Platform Help Tests
    {
        "id": "platform_create_quote",
        "question": "How do I create a quote?",
        "query_type": "platform_help",
        "expected_keywords": ["quote", "create", "click", "select"],
        "must_not_contain": ["I don't know"],
        "criteria": "Should provide step-by-step instructions"
    },
    {
        "id": "platform_send_invoice",
        "question": "How can I send an invoice to a client?",
        "query_type": "platform_help",
        "expected_keywords": ["invoice", "send", "client", "email"],
        "must_not_contain": ["I don't know"],
        "criteria": "Should explain invoice sending process"
    },
    # Pricing Tests
    {
        "id": "pricing_seychelles",
        "question": "What are the rates for Seychelles resorts?",
        "query_type": "pricing",
        "expected_keywords": ["seychelles", "rate", "price"],
        "must_not_contain": [],
        "criteria": "Should provide pricing info or explain where to find it"
    },
    # Destination Tests
    {
        "id": "destination_kenya_safari",
        "question": "Tell me about Kenya safari options",
        "query_type": "destination",
        "expected_keywords": ["kenya", "safari"],
        "must_not_contain": [],
        "criteria": "Should describe Kenya safari experiences"
    },
    # Comparison Tests
    {
        "id": "compare_mauritius_maldives",
        "question": "Compare Mauritius vs Maldives for a honeymoon",
        "query_type": "comparison",
        "expected_keywords": ["mauritius", "maldives"],
        "must_not_contain": [],
        "criteria": "Should compare both destinations with pros/cons"
    },
    # Edge Cases
    {
        "id": "unknown_topic",
        "question": "What's the weather like on Mars?",
        "query_type": "general",
        "expected_keywords": [],
        "must_contain_any": ["don't have", "not sure", "can't find", "knowledge base", "try", "help"],
        "must_not_contain": ["Mars has", "The weather on Mars"],
        "criteria": "Should gracefully decline with helpful suggestions"
    },
    {
        "id": "greeting",
        "question": "Hi, how are you?",
        "query_type": "general",
        "expected_keywords": [],
        "must_not_contain": ["I don't know"],
        "criteria": "Should respond warmly and offer help"
    }
]


def score_response(response: dict, test_case: dict) -> dict:
    """
    Score a response against test case criteria.

    Returns scoring breakdown:
    - keyword_score: Percentage of expected keywords found
    - forbidden_score: 1.0 if no forbidden phrases, 0.0 otherwise
    - response_quality: Based on method used (rag=1.0, fallback=0.7, static=0.5)
    - overall_score: Weighted average
    """
    answer = response.get('answer', '').lower()
    method = response.get('method', 'unknown')

    # Keyword matching
    expected_keywords = test_case.get('expected_keywords', [])
    if expected_keywords:
        found_keywords = sum(1 for kw in expected_keywords if kw.lower() in answer)
        keyword_score = found_keywords / len(expected_keywords)
    else:
        keyword_score = 1.0  # No keywords required

    # Must contain any (for edge cases)
    must_contain_any = test_case.get('must_contain_any', [])
    if must_contain_any:
        if any(phrase.lower() in answer for phrase in must_contain_any):
            contain_any_score = 1.0
        else:
            contain_any_score = 0.0
    else:
        contain_any_score = 1.0

    # Forbidden phrases
    forbidden = test_case.get('must_not_contain', [])
    if forbidden:
        has_forbidden = any(phrase.lower() in answer for phrase in forbidden)
        forbidden_score = 0.0 if has_forbidden else 1.0
    else:
        forbidden_score = 1.0

    # Response quality based on method
    method_scores = {
        'rag': 1.0,
        'fallback': 0.7,
        'static': 0.5,
        'no_results': 0.6,  # Graceful handling is okay
        'unknown': 0.3
    }
    quality_score = method_scores.get(method, 0.3)

    # Overall score (weighted)
    overall = (
        keyword_score * 0.35 +
        contain_any_score * 0.15 +
        forbidden_score * 0.25 +
        quality_score * 0.25
    )

    return {
        "keyword_score": round(keyword_score, 2),
        "contain_any_score": round(contain_any_score, 2),
        "forbidden_score": round(forbidden_score, 2),
        "quality_score": round(quality_score, 2),
        "overall_score": round(overall, 2),
        "passed": overall >= 0.7  # 70% threshold
    }


@helpdesk_router.get("/accuracy-test")
async def run_accuracy_tests(
    test_id: Optional[str] = None,
    verbose: bool = False
):
    """
    Run accuracy tests on the helpdesk RAG system.

    Tests cover:
    - Hotel information queries (various destinations)
    - Platform help queries
    - Pricing queries
    - Destination information
    - Comparison queries
    - Edge cases (unknown topics, greetings)

    Args:
        test_id: Run a specific test by ID, or all if not specified
        verbose: Include full responses in output

    Returns:
        - overall_accuracy: Percentage of tests passed
        - tests: Individual test results with scores
    """
    results = []
    test_cases = ACCURACY_TEST_CASES

    # Filter to specific test if requested
    if test_id:
        test_cases = [t for t in test_cases if t['id'] == test_id]
        if not test_cases:
            return {
                "success": False,
                "error": f"Test '{test_id}' not found",
                "available_tests": [t['id'] for t in ACCURACY_TEST_CASES]
            }

    for test_case in test_cases:
        try:
            # Get search params for this query type
            classifier = get_query_classifier()
            query_type, _ = classifier.classify(test_case['question'])
            search_params = classifier.get_search_params(query_type)

            # Run the search
            start_time = time.time()
            kb_results = search_shared_faiss_index(
                test_case['question'],
                top_k=search_params.get('k', 5),
                use_mmr=search_params.get('use_mmr', False),
                lambda_mmr=search_params.get('lambda_mmr', 0.7),
                use_rerank=search_params.get('use_rerank', False)
            )

            # Generate response
            if kb_results:
                response = generate_rag_response(
                    test_case['question'],
                    kb_results,
                    query_type.value
                )
            else:
                # Use static response
                answer, _, sources = get_smart_response(test_case['question'])
                response = {
                    'answer': answer,
                    'sources': sources,
                    'method': 'static'
                }

            elapsed = time.time() - start_time

            # Score the response
            scores = score_response(response, test_case)

            result = {
                "test_id": test_case['id'],
                "question": test_case['question'],
                "expected_type": test_case['query_type'],
                "actual_type": query_type.value,
                "method": response.get('method', 'unknown'),
                "scores": scores,
                "passed": scores['passed'],
                "time_ms": int(elapsed * 1000),
                "criteria": test_case['criteria']
            }

            if verbose:
                result["answer_preview"] = response['answer'][:300] + "..." if len(response['answer']) > 300 else response['answer']
                result["sources_count"] = len(response.get('sources', []))

            results.append(result)

        except Exception as e:
            results.append({
                "test_id": test_case['id'],
                "question": test_case['question'],
                "passed": False,
                "error": str(e)
            })

    # Calculate overall accuracy
    passed_count = sum(1 for r in results if r.get('passed', False))
    total_count = len(results)
    accuracy = (passed_count / total_count * 100) if total_count > 0 else 0

    # Categorize by quality
    excellent = sum(1 for r in results if r.get('scores', {}).get('overall_score', 0) >= 0.85)
    good = sum(1 for r in results if 0.7 <= r.get('scores', {}).get('overall_score', 0) < 0.85)
    needs_work = sum(1 for r in results if r.get('scores', {}).get('overall_score', 0) < 0.7)

    return {
        "success": True,
        "summary": {
            "total_tests": total_count,
            "passed": passed_count,
            "failed": total_count - passed_count,
            "accuracy_percent": round(accuracy, 1),
            "quality_breakdown": {
                "excellent": excellent,
                "good": good,
                "needs_improvement": needs_work
            }
        },
        "tests": results,
        "target": "80-100% accuracy for production readiness"
    }


@helpdesk_router.get("/accuracy-test/cases")
async def list_accuracy_test_cases() -> Dict[str, Any]:
    """List all available accuracy test cases."""
    return {
        "success": True,
        "test_cases": [
            {
                "id": t['id'],
                "question": t['question'],
                "query_type": t['query_type'],
                "criteria": t['criteria']
            }
            for t in ACCURACY_TEST_CASES
        ]
    }


# ============================================================
# ROUTER REGISTRATION
# ============================================================

def include_helpdesk_router(app: Any) -> None:
    """Include helpdesk router in the FastAPI app"""
    app.include_router(helpdesk_router)
