"""
Helpdesk API Routes - Internal Support (Lite Version)

Provides AI-powered helpdesk support for travel agents.
Uses Travel Platform RAG API for knowledge base queries.
Falls back to helpful static responses when no knowledge base results.

Key features:
- Query classification for optimized search and responses
- MMR (Maximal Marginal Relevance) for diverse hotel options
- Re-ranking for improved relevance
- Natural conversational responses via GPT-4o-mini
"""

import logging
import time
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config.loader import ClientConfig
from src.api.dependencies import get_client_config
from src.middleware.auth_middleware import get_current_user_optional
from src.services.rag_response_service import generate_rag_response, get_rag_service
from src.services.query_classifier import get_query_classifier, QueryType
from src.services.reranker_service import get_reranker
from src.services.travel_platform_rag_client import get_travel_platform_rag_client
from src.api.knowledge_routes import get_index_manager

logger = logging.getLogger(__name__)

helpdesk_router = APIRouter(prefix="/api/v1/helpdesk", tags=["Helpdesk"])


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
# KNOWLEDGE BASE SEARCH HELPER (Two-Tier: Global + Private)
# ============================================================

def search_private_knowledge_base(
    config: ClientConfig,
    query: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Search the tenant's private knowledge base.

    This searches documents uploaded by the tenant with visibility="private".

    Args:
        config: Client configuration for tenant isolation
        query: Search query
        top_k: Number of results

    Returns:
        List of results with 'content', 'score', 'source', 'visibility'
    """
    try:
        if not config:
            logger.warning("No client config for private KB search")
            return []

        logger.info(f"[Private KB] Searching for tenant {config.client_id}: '{query[:50]}...'")

        manager = get_index_manager(config)

        # Search private documents only
        # Using very low threshold (0.05) because the improved search algorithm
        # uses keyword overlap ratio which naturally produces lower but meaningful scores
        results = manager.search(
            query=query,
            top_k=top_k,
            visibility="private",  # Only search tenant's private docs
            min_score=0.05  # Low threshold - let the LLM decide relevance
        )

        # Transform to standard format with source marker
        transformed = []
        for r in results:
            transformed.append({
                "content": r.get("content", ""),
                "score": r.get("score", 0.0),
                "source": r.get("source", "Private Knowledge Base"),
                "source_type": "private_kb",
                "visibility": "private",
                "document_id": r.get("document_id", ""),
                "chunk_index": r.get("chunk_index", 0),
                "match_details": r.get("match_details")  # Pass through debug info
            })

        if transformed:
            logger.info(
                f"[Private KB] Found {len(transformed)} results for tenant {config.client_id}, "
                f"top score: {transformed[0]['score']:.3f}"
            )
        else:
            logger.info(f"[Private KB] No results found for tenant {config.client_id}")

        return transformed

    except Exception as e:
        logger.warning(f"Private KB search failed: {e}", exc_info=True)
        return []


def search_dual_knowledge_base(
    config: ClientConfig,
    query: str,
    top_k: int = 10,
    use_rerank: bool = True
) -> Dict[str, Any]:
    """
    Search BOTH global (Travel Platform RAG) and private knowledge bases.

    Merges results from both sources and ranks by relevance score.

    Args:
        config: Client configuration for tenant isolation
        query: Search query
        top_k: Total number of results to return
        use_rerank: Whether to use re-ranking (default True)

    Returns:
        Dict with 'success', 'answer', 'citations', 'sources_breakdown'
    """
    # Search both knowledge bases in parallel concept (sequential for simplicity)

    # 1. Search Global KB (Travel Platform RAG)
    global_result = search_travel_platform_rag(query, top_k=top_k, use_rerank=use_rerank)
    global_citations = []
    global_answer = ""

    # Content that shouldn't appear in helpdesk answers (managed externally)
    _IRRELEVANT_CONTENT = ["cancellation policy", "cancellation fee", "booking cancellation"]

    if global_result.get("success"):
        global_answer = global_result.get("answer", "")
        global_citations = [
            {
                "content": c.get("content", ""),
                "score": c.get("relevance_score", c.get("score", 0.0)),
                "source": c.get("source_title", "Global Knowledge Base"),
                "source_type": "global_kb",
                "visibility": "public"
            }
            for c in global_result.get("citations", [])
            if not any(phrase in (c.get("content", "") or "").lower() for phrase in _IRRELEVANT_CONTENT)
        ]

    # 2. Search Private KB
    private_results = search_private_knowledge_base(config, query, top_k=top_k)

    # 3. Merge and rank results
    # Note: global_citations have visibility="public", private_results have visibility="private".
    # Each source is pre-filtered by its respective search function.
    all_citations = global_citations + private_results

    # Sort by score descending
    all_citations.sort(key=lambda x: x.get("score", 0), reverse=True)

    # Take top results
    merged_citations = all_citations[:top_k]

    # Count sources for breakdown
    global_count = sum(1 for c in merged_citations if c.get("source_type") == "global_kb")
    private_count = sum(1 for c in merged_citations if c.get("source_type") == "private_kb")

    logger.info(
        f"Dual KB search: {len(global_citations)} global + {len(private_results)} private "
        f"= {len(merged_citations)} merged results"
    )

    return {
        "success": len(merged_citations) > 0 or bool(global_answer),
        "answer": global_answer,  # Use global RAG answer if available
        "citations": merged_citations,
        "confidence": global_result.get("confidence", 0) if global_result.get("success") else 0,
        "latency_ms": global_result.get("latency_ms", 0),
        "sources_breakdown": {
            "global": global_count,
            "private": private_count,
            "total": len(merged_citations)
        }
    }


def search_travel_platform_rag(
    query: str,
    top_k: int = 5,
    use_rerank: bool = True
) -> Dict[str, Any]:
    """
    Search the Travel Platform RAG API for knowledge base queries.

    This uses the centralized Travel Platform RAG service.

    Args:
        query: Search query
        top_k: Number of results (default 5)
        use_rerank: Whether to use re-ranking (default True)

    Returns:
        Dict with 'success', 'answer', 'citations', 'confidence', 'latency_ms', 'query_id'
    """
    try:
        client = get_travel_platform_rag_client()

        if not client.is_available():
            logger.warning("Travel Platform RAG not available")
            return {"success": False, "answer": "", "citations": [], "error": "RAG service unavailable"}

        result = client.search(
            query=query,
            top_k=top_k,
            include_shared=True,
            use_rerank=use_rerank,
        )

        if result.get("success"):
            logger.info(
                f"Travel Platform RAG search: query='{query[:50]}...', "
                f"confidence={result.get('confidence', 0):.2f}"
            )
        else:
            logger.warning(f"Travel Platform RAG search failed: {result.get('error')}")

        return result

    except Exception as e:
        logger.error(f"Travel Platform RAG search error: {e}", exc_info=True)
        return {"success": False, "answer": "", "citations": [], "error": "Knowledge search temporarily unavailable"}


def search_knowledge_base(
    config: ClientConfig,
    query: str,
    top_k: int = 10,
    use_mmr: bool = False,
    lambda_mmr: float = 0.7,
    fetch_k: int = 15,
    use_rerank: bool = True
) -> List[Dict[str, Any]]:
    """
    Search knowledge base via Travel Platform RAG.

    This uses the centralized Travel Platform RAG API.
    The use_mmr, lambda_mmr, and fetch_k params are kept for API compatibility
    but are handled by the Travel Platform service.

    Args:
        config: Client configuration (for compatibility)
        query: Search query
        top_k: Number of results
        use_mmr: Ignored (handled by Travel Platform)
        lambda_mmr: Ignored (handled by Travel Platform)
        fetch_k: Ignored (handled by Travel Platform)
        use_rerank: Whether to use re-ranking

    Returns:
        List of search results with 'content', 'score', 'source'
    """
    result = search_travel_platform_rag(query, top_k=top_k)

    if not result.get("success"):
        logger.warning(f"Travel Platform RAG failed, returning empty: {result.get('error')}")
        return []

    # Transform citations to the format expected by the rest of the code
    citations = result.get("citations", [])
    transformed = []

    for cite in citations:
        transformed.append({
            "content": cite.get("content", ""),
            "score": cite.get("relevance_score", cite.get("score", 0.0)),
            "source": cite.get("source_title", "Knowledge Base"),
            "source_url": cite.get("source_url", ""),
            "doc_id": cite.get("doc_id", ""),
            "chunk_id": cite.get("chunk_id", "")
        })

    return transformed


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


# Travel-related query types that benefit from web search supplementation
_WEB_SEARCH_QUERY_TYPES = {
    QueryType.DESTINATION_INFO,
    QueryType.HOTEL_INFO,
    QueryType.GENERAL,
}


def _web_search_supplement(question: str, query_type: QueryType, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Perform a web search to supplement KB results for travel queries.

    Uses DuckDuckGo HTML search (no API key needed).
    Returns list of citation-like dicts with 'content', 'source', 'score', 'source_type'.
    """
    if query_type not in _WEB_SEARCH_QUERY_TYPES:
        return []

    import httpx
    import re as _re

    search_query = question

    try:
        with httpx.Client(timeout=5.0, follow_redirects=True) as client:
            r = client.get(
                "https://html.duckduckgo.com/html/",
                params={"q": search_query},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            )
            r.raise_for_status()

        html = r.text
        results = []

        # Parse result snippets and titles from DDG HTML
        # Primary selectors
        snippets = _re.findall(r'result__snippet[^>]*>(.*?)</[^>]+>', html, _re.DOTALL)
        titles = _re.findall(r'result__a[^>]*>(.*?)</a>', html, _re.DOTALL)
        urls = _re.findall(r'result__url[^>]*href="([^"]*)"', html, _re.DOTALL)
        # Fallback URL extraction
        if not urls:
            urls = _re.findall(r'result__url[^>]*>(.*?)</a>', html, _re.DOTALL)

        # Fallback: if primary selectors fail, try broader patterns
        if not snippets:
            snippets = _re.findall(r'class="[^"]*snippet[^"]*"[^>]*>(.*?)</[^>]+>', html, _re.DOTALL)
        if not titles and not snippets:
            logger.debug("DDG HTML parsing: primary selectors matched nothing, HTML may have changed")
            return []

        for i in range(min(max_results, len(snippets))):
            try:
                title = _re.sub(r'<[^>]+>', '', titles[i]).strip() if i < len(titles) else ''
                snippet = _re.sub(r'<[^>]+>', '', snippets[i]).strip()
                url = urls[i].strip() if i < len(urls) else 'Web Search'
                url = _re.sub(r'<[^>]+>', '', url).strip()

                if snippet and len(snippet) > 20:
                    content = f"{title}: {snippet}" if title else snippet
                    results.append({
                        "content": content,
                        "source": title or url or "Web Search",
                        "source_url": url,
                        "score": 0.6 - (i * 0.05),
                        "source_type": "web_search",
                    })
            except (IndexError, AttributeError) as parse_err:
                logger.debug(f"DDG parse error for result {i}: {parse_err}")
                continue

        logger.info(f"Web search supplement: {len(results)} results for '{search_query[:50]}'")
        return results[:max_results]

    except Exception as e:
        logger.debug(f"Web search supplement failed (non-critical): {e}")
        return []


# Keywords that indicate a question the KB probably can't answer well
_WEB_SEARCH_KEYWORDS = {
    "weather", "climate", "temperature", "rain", "season", "best time",
    "visa", "passport", "currency", "exchange rate", "safety", "vaccine",
    "vaccination", "malaria", "covid", "transport", "airport", "getting there",
    "getting around", "language", "time zone", "plug", "electricity",
    "tipping", "customs", "dress code", "what to pack", "cost of living",
}

_LOW_QUALITY_PHRASES = [
    "couldn't find", "could not find", "don't have",
    "no specific information", "not available in my knowledge",
    "i don't have information", "no information available",
]


def _is_low_quality_answer(answer: str, confidence: float) -> bool:
    """Detect fallback/low-quality RAG answers that should yield to private KB."""
    if confidence < 0.5:
        return True
    lower = answer.lower()
    return any(phrase in lower for phrase in _LOW_QUALITY_PHRASES)


# ============================================================
# ENDPOINTS
# ============================================================

@helpdesk_router.post("/ask")
def ask_helpdesk(
    request: AskQuestion,
    user: Optional[dict] = Depends(get_current_user_optional),
    config: ClientConfig = Depends(get_client_config)
):
    """
    Ask a question to the helpdesk assistant.
    Uses Travel Platform RAG for knowledge base queries.
    Falls back to smart static responses if RAG unavailable.

    Features:
    - Query classification for optimized search parameters
    - Travel Platform RAG with re-ranking
    - Natural conversational responses
    - Fallback to static help content

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

        # Step 2: Search BOTH knowledge bases (Global + Private)
        search_start = time.time()
        dual_result = search_dual_knowledge_base(
            config,
            question,
            top_k=search_params.get('k', 10),
            use_rerank=search_params.get('use_rerank', True)
        )
        search_time = time.time() - search_start

        # Check if we have ANY results from the dual-KB search
        citations = dual_result.get("citations", [])
        global_answer = dual_result.get("answer", "")
        sources_breakdown = dual_result.get("sources_breakdown", {})

        # Check if this is a practical travel question that the KB can't answer well.
        # For questions about weather, visas, currency etc., the KB only has hotel
        # fact sheets — web search will give a MUCH better answer.
        q_lower = question.lower()
        needs_web_search = any(kw in q_lower for kw in _WEB_SEARCH_KEYWORDS)

        if dual_result.get("success") and global_answer and not needs_web_search:
            # Check if private KB has better results before returning global answer
            has_private_kb = any(
                c.get("source_type") == "private_kb" and c.get("score", 0) >= 0.2
                for c in citations
            )
            if has_private_kb and _is_low_quality_answer(global_answer, dual_result.get("confidence", 0)):
                logger.info("Global answer low-quality, private KB has results — using LLM synthesis")
            else:
                # Got a synthesized answer from global KB (Travel Platform RAG)
                total_time = time.time() - start_time
                logger.info(
                    f"Helpdesk dual-KB: search={search_time:.2f}s, total={total_time:.2f}s, "
                    f"global={sources_breakdown.get('global', 0)}, private={sources_breakdown.get('private', 0)}"
                )

                if total_time > 3.0:
                    logger.warning(f"Helpdesk response exceeded 3s target: {total_time:.2f}s")

                # Format citations as sources, marking their origin
                sources = []
                for cite in citations[:5]:
                    source_type = cite.get("source_type", "global_kb")
                    sources.append({
                        "filename": cite.get("source", "Knowledge Base"),
                        "score": cite.get("score", 0),
                        "type": source_type,
                        "is_private": source_type == "private_kb"
                    })

                return {
                    "success": True,
                    "answer": global_answer,
                    "sources": sources,
                    "method": "dual_kb",
                    "query_type": query_type.value if hasattr(query_type, 'value') else str(query_type),
                    "confidence": dual_result.get("confidence", 0),
                    "sources_breakdown": sources_breakdown,
                    "timing": {
                        "search_ms": int(search_time * 1000),
                        "synthesis_ms": 0,  # Synthesis done by Travel Platform
                        "total_ms": int(total_time * 1000),
                        "rag_latency_ms": dual_result.get("latency_ms", 0)
                    }
                }

        if needs_web_search:
            logger.info(f"Question matches web search keywords, will supplement KB with web search")

        # Step 3: Check if we have private KB results that need LLM synthesis
        # Filter out low-relevance results (score < 0.2) to avoid citing irrelevant documents
        private_results = [
            c for c in citations
            if c.get("source_type") == "private_kb" and c.get("score", 0) >= 0.2
        ]

        if private_results:
            # We have relevant private KB results - synthesize an answer using LLM
            # If needs_web_search is True, also run web search and combine both
            # sources so the LLM gets KB context AND external info (weather, visa, etc.)
            web_supplement = []
            web_supplement_sources = []
            if needs_web_search:
                logger.info(f"Running web search to supplement {len(private_results)} KB results")
                web_supplement = _web_search_supplement(question, query_type)
                web_supplement_sources = [
                    {"filename": r.get("source", "Web Search"), "score": r.get("score", 0.5), "type": "web_search"}
                    for r in web_supplement
                ]
            else:
                logger.info(f"Found {len(private_results)} relevant private KB results (score >= 0.4), using LLM synthesis")

            # Combine KB results + web search results for richer LLM context
            combined_results = private_results + web_supplement

            synthesis_start = time.time()
            try:
                rag_service = get_rag_service()
                llm_response = rag_service.generate_response(
                    question=question,
                    search_results=combined_results,
                    query_type=query_type.value if hasattr(query_type, 'value') else str(query_type)
                )
                synthesis_time = time.time() - synthesis_start
                total_time = time.time() - start_time

                method = "private_kb_synthesis" if not web_supplement else "combined_kb_web_synthesis"
                logger.info(
                    f"Helpdesk {method}: search={search_time:.2f}s, "
                    f"synthesis={synthesis_time:.2f}s, total={total_time:.2f}s, "
                    f"kb={len(private_results)}, web={len(web_supplement)}"
                )

                # Format sources — KB sources first, then web sources
                sources = []
                for r in private_results[:5]:
                    sources.append({
                        "filename": r.get("source", "Private Knowledge Base"),
                        "score": r.get("score", 0),
                        "type": "private_kb",
                        "is_private": True
                    })
                sources.extend(web_supplement_sources)

                return {
                    "success": True,
                    "answer": llm_response.get("answer", ""),
                    "sources": sources,
                    "method": method,
                    "query_type": query_type.value if hasattr(query_type, 'value') else str(query_type),
                    "sources_breakdown": {
                        "global": 0,
                        "private": len(private_results),
                        "web": len(web_supplement),
                        "total": len(combined_results)
                    },
                    "timing": {
                        "search_ms": int(search_time * 1000),
                        "synthesis_ms": int(synthesis_time * 1000),
                        "total_ms": int(total_time * 1000)
                    }
                }
            except Exception as synth_error:
                logger.warning(f"Private KB synthesis failed: {synth_error}")
                # Fall through to static responses

        # Step 4: Try smart static responses (faster, no LLM cost)
        # These are high-quality pre-written responses for common questions
        static_answer, topic, static_sources = get_smart_response(question)

        # If we got a non-default static response, use it
        if topic != "general" or "quote" in question.lower() or "invoice" in question.lower():
            total_time = time.time() - start_time
            logger.info(f"Helpdesk using smart static response: topic={topic}")

            return {
                "success": True,
                "answer": static_answer,
                "sources": static_sources,
                "method": "smart_static",
                "query_type": query_type.value if hasattr(query_type, 'value') else str(query_type),
                "note": "Knowledge base is being configured. This response is from our curated help content.",
                "timing": {
                    "search_ms": int(search_time * 1000),
                    "synthesis_ms": 0,
                    "total_ms": int(total_time * 1000)
                }
            }

        # Step 5: For unknown topics or practical travel questions, use LLM with web search.
        # Web search is triggered when:
        #   - needs_web_search is True (weather, visa, currency questions)
        #   - OR KB results are sparse (< 3 citations) for travel-related queries
        logger.info(f"Using LLM synthesis (citations={len(citations)}, needs_web={needs_web_search})")

        # Supplement with web search for travel questions
        # Trigger web search when:
        #   - needs_web_search is True (weather, visa, currency keywords)
        #   - OR KB results are sparse (< 3 citations) for travel queries
        #   - OR KB results exist but are all low relevance (< 0.45 max score)
        all_context = list(citations)
        web_sources = []
        max_citation_score = max((c.get("score", 0) for c in citations), default=0) if citations else 0
        should_web_search = needs_web_search or (
            (len(citations) < 3 or max_citation_score < 0.45)
            and query_type in _WEB_SEARCH_QUERY_TYPES
        )
        if should_web_search:
            web_results = _web_search_supplement(question, query_type)
            all_context.extend(web_results)
            web_sources = [
                {"filename": r.get("source", "Web Search"), "score": r.get("score", 0.5), "type": "web_search"}
                for r in web_results
            ]

        synthesis_start = time.time()
        try:
            rag_service = get_rag_service()
            # Use KB citations + web search results for richer context
            llm_response = rag_service.generate_response(
                question=question,
                search_results=all_context,
                query_type=query_type.value if hasattr(query_type, 'value') else str(query_type)
            )
            synthesis_time = time.time() - synthesis_start
            total_time = time.time() - start_time

            method = "llm_synthesis" if not web_sources else "llm_synthesis_web"
            logger.info(f"Helpdesk LLM fallback ({method}): synthesis={synthesis_time:.2f}s, total={total_time:.2f}s")

            # Merge sources: LLM sources + web sources
            combined_sources = llm_response.get("sources", []) + web_sources

            return {
                "success": True,
                "answer": llm_response.get("answer", "I'm not sure how to help with that. Could you try rephrasing your question?"),
                "sources": combined_sources,
                "method": method,
                "query_type": query_type.value if hasattr(query_type, 'value') else str(query_type),
                "timing": {
                    "search_ms": int(search_time * 1000),
                    "synthesis_ms": int(synthesis_time * 1000),
                    "total_ms": int(total_time * 1000)
                }
            }
        except Exception as llm_error:
            logger.warning(f"LLM synthesis failed: {llm_error}, using static fallback")
            total_time = time.time() - start_time

            # Final fallback: use the default static response
            return {
                "success": True,
                "answer": static_answer,  # Use default static response
                "sources": [],
                "method": "static_fallback",
                "query_type": query_type.value if hasattr(query_type, 'value') else str(query_type),
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
def get_helpdesk_topics(
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
def search_helpdesk(
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


@helpdesk_router.get("/rag-status")
def get_rag_status() -> Dict[str, Any]:
    """
    Get status of the Travel Platform RAG connection.
    Useful for debugging and monitoring.
    """
    try:
        client = get_travel_platform_rag_client()
        return {
            "success": True,
            "data": client.get_status()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@helpdesk_router.get("/faiss-status")
def get_faiss_status() -> Dict[str, Any]:
    """
    Legacy endpoint - redirects to /rag-status.
    Kept for backward compatibility.
    """
    return get_rag_status()


@helpdesk_router.get("/test-search")
def test_rag_search(q: str = "Maldives hotels"):
    """
    Test endpoint for Travel Platform RAG search (no auth required).
    For debugging and verification only.

    Returns the RAG response with answer and citations.
    """
    try:
        result = search_travel_platform_rag(q, top_k=10)

        if result.get("success") and result.get("answer"):
            answer = result["answer"]
            return {
                "success": True,
                "query": q,
                "method": "travel_platform_rag",
                "confidence": result.get("confidence", 0),
                "latency_ms": result.get("latency_ms", 0),
                "citations_count": len(result.get("citations", [])),
                "citations": [
                    {
                        "source_title": c.get("source_title", "Unknown"),
                        "relevance_score": c.get("relevance_score", c.get("score", 0)),
                        "content_preview": c.get("content", "")[:200] + "..." if len(c.get("content", "")) > 200 else c.get("content", "")
                    }
                    for c in result.get("citations", [])[:5]
                ],
                "answer_preview": answer[:500] + "..." if len(answer) > 500 else answer
            }
        else:
            return {
                "success": False,
                "query": q,
                "method": "travel_platform_rag",
                "error": result.get("error", "No answer returned"),
                "message": "Travel Platform RAG did not return an answer"
            }

    except Exception as e:
        logger.error(f"Test search failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@helpdesk_router.get("/health")
def helpdesk_health() -> Dict[str, Any]:
    """
    Health check endpoint for the helpdesk RAG system.

    Verifies Travel Platform RAG is available and working.

    Returns:
        - status: "healthy" if Travel Platform RAG available, "degraded" otherwise
        - mode: "travel_platform_rag" or "static_fallback"
        - checks: Individual component status
    """
    try:
        # Get Travel Platform RAG status
        rag_client = get_travel_platform_rag_client()
        tp_status = rag_client.get_status()
        tp_available = tp_status.get("available", False)

        # Determine overall health
        checks = {
            "travel_platform_rag_available": tp_available,
            "travel_platform_url": tp_status.get("base_url", ""),
            "travel_platform_tenant": tp_status.get("tenant", ""),
        }

        # Health is "healthy" if Travel Platform RAG is available
        status = "healthy" if tp_available else "degraded"
        mode = "travel_platform_rag" if tp_available else "static_fallback"

        return {
            "status": status,
            "mode": mode,
            "checks": checks,
            "details": {
                "travel_platform": tp_status
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
def agent_chat(
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
def agent_reset() -> Dict[str, Any]:
    """Reset the agent's conversation history for a new session."""
    try:
        from src.agents.helpdesk_agent import get_helpdesk_agent
        agent = get_helpdesk_agent()
        agent.reset_conversation()
        return {"success": True, "message": "Conversation reset"}
    except Exception as e:
        return {"success": False, "error": str(e)}


@helpdesk_router.get("/agent/stats")
def agent_stats() -> Dict[str, Any]:
    """Get agent statistics."""
    try:
        from src.agents.helpdesk_agent import get_helpdesk_agent
        agent = get_helpdesk_agent()
        return {"success": True, "stats": agent.get_stats()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@helpdesk_router.post("/reinit")
def reinit_rag_client():
    """
    Reinitialize the Travel Platform RAG client.

    Use this after changing TRAVEL_PLATFORM_URL, TRAVEL_PLATFORM_API_KEY,
    or TRAVEL_PLATFORM_TENANT environment variables.
    """
    try:
        from src.services.travel_platform_rag_client import (
            get_travel_platform_rag_client,
            reset_travel_platform_rag_client
        )

        # Reset and reinitialize
        reset_travel_platform_rag_client()

        # Get fresh client
        client = get_travel_platform_rag_client()
        available = client.is_available()

        status = client.get_status()

        return {
            "success": available,
            "message": "Travel Platform RAG client reinitialized" if available else "RAG service unavailable",
            "status": status
        }

    except Exception as e:
        logger.error(f"RAG client reinit failed: {e}", exc_info=True)
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
        'travel_platform_rag': 1.0,
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
def run_accuracy_tests(
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

            # Run the search via Travel Platform RAG
            start_time = time.time()
            rag_result = search_travel_platform_rag(
                test_case['question'],
                top_k=search_params.get('k', 5)
            )

            # Generate response
            if rag_result.get("success") and rag_result.get("answer"):
                # Travel Platform RAG already has the synthesized answer
                response = {
                    'answer': rag_result.get("answer", ""),
                    'sources': [
                        {"source": c.get("source_title", ""), "score": c.get("relevance_score", c.get("score", 0))}
                        for c in rag_result.get("citations", [])
                    ],
                    'method': 'travel_platform_rag'
                }
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
                "actual_type": query_type.value if hasattr(query_type, 'value') else str(query_type),
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
def list_accuracy_test_cases() -> Dict[str, Any]:
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
