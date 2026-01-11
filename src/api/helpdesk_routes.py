"""
Helpdesk API Routes - Internal Support (Lite Version)

Provides AI-powered helpdesk support for travel agents.
This is a simplified version that returns helpful static responses.
"""

import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from config.loader import ClientConfig
from src.middleware.auth_middleware import get_current_user

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
# STATIC HELP RESPONSES
# ============================================================

HELP_RESPONSES = {
    "quote": """To create a quote:
1. Go to Quotes > Generate Quote
2. Enter client details and travel requirements
3. Select hotels and add pricing
4. Click 'Generate Quote' to create the document
5. Share via email or download as PDF""",

    "invoice": """To create an invoice:
1. Open an accepted quote
2. Click 'Convert to Invoice'
3. Review the invoice details
4. Send to client or mark as paid""",

    "client": """To manage clients:
1. Go to CRM > All Clients
2. Click 'Add Client' for new entries
3. Use the Pipeline view to track client stages
4. Add notes and activities to client records""",

    "hotel": """To search hotels:
1. Go to Pricing > Hotels
2. Use filters for location, dates, and amenities
3. Click on a hotel to see rates and availability
4. Add hotels to quotes directly from the list""",

    "default": """I'm here to help with your travel platform questions.

You can ask about:
- Creating and managing quotes
- Invoice generation and billing
- Client relationship management
- Hotel search and pricing
- System settings and configuration

What would you like help with?"""
}


# ============================================================
# ENDPOINTS
# ============================================================

@helpdesk_router.post("/ask")
async def ask_helpdesk(
    request: AskQuestion,
    user: dict = Depends(get_current_user)
):
    """
    Ask a question to the helpdesk assistant.
    Returns a helpful response based on the question topic.
    """
    try:
        question = request.question.lower()

        # Simple keyword matching for responses
        if any(word in question for word in ["quote", "pricing", "price"]):
            answer = HELP_RESPONSES["quote"]
            topic = "quotes"
        elif any(word in question for word in ["invoice", "bill", "payment"]):
            answer = HELP_RESPONSES["invoice"]
            topic = "invoices"
        elif any(word in question for word in ["client", "customer", "contact"]):
            answer = HELP_RESPONSES["client"]
            topic = "clients"
        elif any(word in question for word in ["hotel", "rate", "room", "accommodation"]):
            answer = HELP_RESPONSES["hotel"]
            topic = "hotels"
        else:
            answer = HELP_RESPONSES["default"]
            topic = "general"

        return {
            "success": True,
            "answer": answer,
            "sources": [{"topic": topic, "type": "helpdesk"}]
        }

    except Exception as e:
        logger.error(f"Helpdesk error: {e}")
        return {
            "success": False,
            "answer": "I'm having trouble processing your question. Please try again or contact support.",
            "sources": []
        }


@helpdesk_router.get("/topics")
async def get_helpdesk_topics(
    user: dict = Depends(get_current_user)
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
    user: dict = Depends(get_current_user)
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


# ============================================================
# ROUTER REGISTRATION
# ============================================================

def include_helpdesk_router(app):
    """Include helpdesk router in the FastAPI app"""
    app.include_router(helpdesk_router)
