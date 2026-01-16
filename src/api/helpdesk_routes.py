"""
Helpdesk API Routes - Internal Support (Lite Version)

Provides AI-powered helpdesk support for travel agents.
Connects to local FAISS knowledge base for contextual answers.
Falls back to helpful static responses when no knowledge base results.
"""

import logging
import os
import time
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel

from config.loader import ClientConfig
from src.middleware.auth_middleware import get_current_user_optional
from src.services.rag_response_service import generate_rag_response

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
    "quote_create": """Great question! Creating a quote is straightforward:

**Here's how to do it:**
1. Head over to **Quotes** in the sidebar, then click **Generate Quote**
2. Fill in your client's details and what they're looking for
3. Pick the hotels and accommodations that fit their needs
4. Add any extras or special requests
5. Hit **Generate Quote** and you're done!

The quote gets saved automatically, and you can email it directly to your client or download it as a PDF. Let me know if you need help with any specific part!""",

    "quote_send": """Sending a quote to your client is super easy:

1. Go to **Quotes** and find the one you want to send
2. Click on it to open the details
3. Look for the **Send Quote** button
4. Double-check the email address and add a personal note if you'd like
5. Hit send!

Your client will receive a professional email with the quote PDF attached. They can view it right in their browser or download it.""",

    "invoice": """Need to create an invoice? Here's the quick way:

**From an existing quote:**
1. Open the quote in your quotes list
2. Click **Convert to Invoice** — this pulls in all the details automatically!

**Or create one from scratch:**
1. Go to **Invoices** in the sidebar
2. Click **Create Invoice**
3. Add your line items, set the due date, and you're set

Once created, you can send it directly to your client and track when they've viewed or paid it.""",

    "client_add": """Adding a new client to your CRM is quick:

1. Go to **CRM** → **All Clients**
2. Click the **Add Client** button
3. Fill in their details (name, email, phone)
4. Pick how they found you (website, referral, etc.)
5. Save it!

From there, you can create quotes for them, track their status in the pipeline, and keep all your notes in one place.""",

    "pipeline": """The Pipeline is your visual sales tracker — think of it as a bird's-eye view of where all your clients are in their journey:

📋 **Quoted** — They've received a quote
💬 **Negotiating** — You're working out the details
✅ **Booked** — Trip confirmed!
💰 **Paid** — Payment received
✈️ **Travelled** — They're on their trip or just got back
❌ **Lost** — Didn't work out this time

**Pro tip:** Just drag and drop clients between stages to update their status. It's that easy!""",

    "hotel": """Looking for hotel info? Here's where to find it:

1. Go to **Pricing Guide** → **Hotels**
2. Use the search and filters to narrow things down by location, star rating, or amenities
3. Click on any hotel to see its full details and current rates

When you're building a quote, you can add hotels directly from this list. The rates update automatically based on the travel dates.""",

    "pricing": """Managing your pricing is all in the **Pricing Guide** section:

- **Rates** — View and update accommodation pricing by date range
- **Hotels** — Browse properties and see their rate structures

Any changes you make here will automatically show up when you create new quotes. You can also import rates from spreadsheets if you've got bulk updates.""",

    "settings": """Want to customize things? Head to **Settings** — you'll find everything there:

- **Profile** — Your personal details
- **Company** — Business info, banking details for invoices
- **Branding** — Your logo, colors, and theme
- **Notifications** — What emails you receive
- **Integrations** — Connected services

Changes save automatically in most cases, but look for the Save button when you're editing sections.""",

    "default": """Hey there! I'm your platform assistant, here to help you get the most out of the system.

**I can help you with:**
- 📄 **Quotes** — Creating, sending, and managing travel quotes
- 👥 **CRM** — Adding clients and tracking them through your pipeline
- 💰 **Invoices** — Generating invoices and tracking payments
- 🏨 **Hotels & Rates** — Finding properties and managing pricing
- ⚙️ **Settings** — Customizing your platform

Just ask me anything specific, like "How do I create a quote?" or "What do the pipeline stages mean?" and I'll walk you through it!"""
}


# ============================================================
# KNOWLEDGE BASE SEARCH HELPER
# ============================================================

def search_shared_faiss_index(query: str):
    """
    Search the shared FAISS helpdesk index (stored in GCS).
    This is the primary knowledge base for helpdesk queries.

    Uses search_with_context for better RAG context:
    - Returns 5-8 documents (top_k=8)
    - Filters by relevance (min_score=0.3)
    - Ensures minimum 3 results for context
    """
    try:
        from src.services.faiss_helpdesk_service import get_faiss_helpdesk_service

        service = get_faiss_helpdesk_service()
        results = service.search_with_context(query, top_k=8, min_score=0.3)

        if results:
            logger.info(f"Shared FAISS search returned {len(results)} results for RAG context")
            return results

    except Exception as e:
        logger.warning(f"Shared FAISS search failed: {e}")

    return []


def search_knowledge_base(config: ClientConfig, query: str, top_k: int = 5):
    """
    Search knowledge bases for relevant content.

    Priority:
    1. Shared FAISS helpdesk index (GCS bucket: zorah-faiss-index)
       - Uses search_with_context (8 docs, min_score 0.3)
    2. Per-tenant local FAISS index (fallback)
    """
    # First try the shared FAISS index (returns 5-8 docs with relevance filtering)
    shared_results = search_shared_faiss_index(query)
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


def format_knowledge_response(results: List[Dict], question: str) -> Dict[str, Any]:
    """
    Format knowledge base results using RAG synthesis.
    Returns dict with 'answer', 'sources', 'method'.
    """
    return generate_rag_response(question, results)


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

    Note: Authentication is optional - helpdesk works for all users.
    Returns timing data for performance monitoring.
    """
    start_time = time.time()

    try:
        question = request.question

        # Step 1: Try knowledge base search
        search_start = time.time()
        kb_results = search_knowledge_base(config, question)
        search_time = time.time() - search_start

        if kb_results:
            # Step 2: RAG synthesis
            synth_start = time.time()
            rag_response = format_knowledge_response(kb_results, question)
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
                "timing": {
                    "search_ms": int(search_time * 1000),
                    "synthesis_ms": int(synth_time * 1000),
                    "total_ms": int(total_time * 1000)
                }
            }

        # Step 2: Fall back to smart static responses
        answer, topic, sources = get_smart_response(question)
        total_time = time.time() - start_time
        logger.info(f"Helpdesk fallback: search={search_time:.2f}s, total={total_time:.2f}s (no KB results)")

        return {
            "success": True,
            "answer": answer,
            "sources": sources,
            "method": "static",
            "timing": {
                "search_ms": int(search_time * 1000),
                "synthesis_ms": 0,
                "total_ms": int(total_time * 1000)
            }
        }

    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"Helpdesk error after {total_time:.2f}s: {e}")
        return {
            "success": False,
            "answer": "Hmm, I ran into a small hiccup processing that. Could you try rephrasing your question? If it keeps happening, feel free to reach out to support!",
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
async def get_faiss_status():
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


# ============================================================
# ROUTER REGISTRATION
# ============================================================

def include_helpdesk_router(app):
    """Include helpdesk router in the FastAPI app"""
    app.include_router(helpdesk_router)
