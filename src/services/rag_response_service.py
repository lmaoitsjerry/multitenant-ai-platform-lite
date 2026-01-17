"""
RAG Response Service - Natural Language Synthesis

Transforms FAISS search results into conversational, helpful responses
using GPT-4o-mini. Handles unknown questions gracefully.

Key improvements:
- Query type-specific prompts for better responses
- Improved system prompt with examples
- Better error handling and API key validation
- Source name cleanup
- Content cleaning for better context
"""

import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


# ============================================================
# SYSTEM PROMPTS
# ============================================================

SYSTEM_PROMPT = """You are Zara, a friendly and knowledgeable travel assistant at Zorah Travel. You help travel agents and tour operators find the perfect properties for their clients.

YOUR PERSONALITY:
- Warm, enthusiastic, and genuinely helpful - like a colleague who loves travel
- Confident in your knowledge but honest when you're unsure
- Professional but personable - not corporate or robotic
- You take pride in helping agents impress their clients

YOUR ROLE:
- Help users find hotels, understand pricing, and use the Zorah platform
- Provide accurate, detailed information from the knowledge base
- Make recommendations based on what suits different types of travelers

RESPONSE STYLE:
1. Answer the question directly first - don't make them wait for the key info
2. Include specific details: hotel names, star ratings, standout features, prices when available
3. Use **bold** for property names to make scanning easy
4. Keep it conversational - 2-4 short paragraphs, not walls of text
5. End with a helpful next step or offer to dig deeper

WHAT TO AVOID:
- Don't start with "Based on the context..." or "I found..." - just answer naturally
- Don't dump raw text or partial sentences from documents
- Don't use bullet lists unless comparing multiple options
- Don't make up information that isn't in the context
- Don't be overly formal or use corporate jargon
- Never say "as an AI" or refer to yourself as artificial

EXAMPLE RESPONSES:

User: "What luxury hotels do you have in Mauritius?"
Zara: "Great choice! Mauritius has some stunning luxury options. **Solana Beach** is one of my favourites - it's on the east coast with 117 sea-facing rooms, each with a private balcony. The service there is really personalised. If your clients want all-inclusive, **Constance Belle Mare** is excellent with world-class dining and direct beach access. Want me to put together a comparison or start a quote for either?"

User: "How do I create a quote?"
Zara: "Super easy! Head to **Quotes** in the sidebar and click **New Quote**. Select your client, pick the destination and travel dates, and the system will show you available properties with current rates. Add what you need, hit **Generate**, and you can email it straight to your client. Takes about 2 minutes once you get the hang of it. Anything specific you're trying to quote right now?"

If you don't have enough information, be honest: "I don't have details on that specific property in my knowledge base, but I can help you find similar options or check the pricing system directly."

Remember: You're Zara from Zorah Travel - be helpful, be human, and help agents look great to their clients."""


# Query type-specific guidance (appended to system prompt)
QUERY_TYPE_PROMPTS = {
    "hotel_info": """
FOCUS FOR THIS QUERY:
- Lead with the best hotel matches and their standout features
- Include star ratings, key amenities, location highlights
- Explain what makes each property unique or special
- Be enthusiastic but professional, like recommending to a colleague""",

    "pricing": """
FOCUS FOR THIS QUERY:
- Be specific about prices, what's included, and any seasonal variations
- Mention value proposition and what guests get for the price
- Be clear and transparent about costs
- If prices vary, explain the range and what affects pricing""",

    "platform_help": """
FOCUS FOR THIS QUERY:
- Provide clear, step-by-step guidance
- Mention specific buttons, pages, or sections to click
- Include tips for efficiency or common pitfalls
- Be patient and helpful, like a colleague showing them around""",

    "destination": """
FOCUS FOR THIS QUERY:
- Paint a picture of what makes the destination special
- Include highlights, best time to visit, types of travelers it suits
- Be inspiring and informative
- Connect the destination to available properties if relevant""",

    "comparison": """
FOCUS FOR THIS QUERY:
- Present key differences between options clearly
- Include pros/cons or who each option suits best
- Give a balanced view but also a recommendation if appropriate
- Help guide their decision without being pushy""",

    "general": """
FOCUS FOR THIS QUERY:
- Answer the question directly and helpfully
- Use information from the context naturally
- Offer to provide more details if needed"""
}


class RAGResponseService:
    """Synthesize natural responses from knowledge base search results"""

    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self._client = None
        self._api_status = self._validate_api_key()

    def _validate_api_key(self) -> Dict[str, Any]:
        """Validate API key on startup"""
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY not set - RAG synthesis will use fallback mode")
            return {"valid": False, "reason": "not_set"}

        if not self.openai_api_key.startswith('sk-'):
            logger.warning("OPENAI_API_KEY format may be invalid (doesn't start with 'sk-')")
            # Don't fail - it might be a project API key or other valid format
            return {"valid": True, "reason": "format_warning"}

        return {"valid": True, "reason": None}

    @property
    def client(self):
        """Lazy-load OpenAI client"""
        if self._client is None and self.openai_api_key:
            try:
                import openai
                self._client = openai.OpenAI(api_key=self.openai_api_key)
                logger.info("OpenAI client initialized for RAG synthesis")
            except Exception as e:
                logger.error(f"Failed to create OpenAI client: {e}")
                self._client = None
        return self._client

    def get_status(self) -> Dict[str, Any]:
        """Get service status for health checks"""
        return {
            "api_key_configured": bool(self.openai_api_key),
            "api_key_valid": self._api_status.get("valid", False),
            "api_status": self._api_status,
            "synthesis_available": self.client is not None,
            "mode": "llm" if self.client else "fallback"
        }

    def generate_response(
        self,
        question: str,
        search_results: List[Dict[str, Any]],
        query_type: str = "general",
        max_context_chars: int = 6000
    ) -> Dict[str, Any]:
        """
        Generate a natural response from search results.

        Args:
            question: User's original question
            search_results: List of dicts with 'content', 'score', 'source'
            query_type: Type of query for optimized prompts
            max_context_chars: Maximum characters of context to include

        Returns:
            Dict with 'answer', 'sources', 'method' ('rag' or 'fallback')
        """
        # No API key - return structured fallback
        if not self.client:
            logger.warning("No OpenAI client available - using fallback response")
            return self._fallback_response(question, search_results)

        # No search results - handle gracefully
        if not search_results:
            return self._no_results_response(question)

        # Build context from search results
        context = self._build_context(search_results, max_context_chars)

        # Generate response
        try:
            answer = self._call_llm(question, context, query_type)
            return {
                'answer': answer,
                'sources': [
                    {'filename': self._clean_source_name(r.get('source', ''), r), 'score': r.get('score', 0)}
                    for r in search_results[:5]  # Top 5 sources
                ],
                'method': 'rag',
                'query_type': query_type
            }
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}", exc_info=True)
            return self._fallback_response(question, search_results)

    def _clean_source_name(self, source: str, result: Optional[Dict] = None) -> str:
        """Clean up source names - convert temp file paths to friendly names"""
        if not source:
            return "Knowledge Base"

        # Check for metadata title first (preferred)
        if result:
            metadata = result.get('metadata', {})
            if isinstance(metadata, dict):
                title = metadata.get('title') or metadata.get('name')
                if title and not title.startswith('tmp') and '/tmp' not in title:
                    return title

        # Extract filename from path
        if '/' in source or '\\' in source:
            # Get just the filename
            filename = source.replace('\\', '/').split('/')[-1]

            # Detect temp file patterns
            is_temp = any([
                filename.startswith('tmp'),
                '/tmp' in source.lower(),
                '\\tmp' in source.lower(),
                '/temp' in source.lower(),
                '\\temp' in source.lower(),
                'temp' in source.lower() and 'template' not in source.lower(),
                '/var/folders/' in source,  # macOS temp
                'appdata\\local\\temp' in source.lower(),  # Windows temp
            ])

            if is_temp:
                # Try to extract meaningful info from the content
                if result and result.get('content'):
                    content = result['content']
                    # Look for hotel names or document titles in content
                    if 'hotel' in content.lower() or 'resort' in content.lower():
                        return "Hotel Information"
                    elif 'rate' in content.lower() or 'price' in content.lower():
                        return "Pricing Guide"
                    elif 'maldives' in content.lower():
                        return "Maldives Guide"
                    elif 'mauritius' in content.lower():
                        return "Mauritius Guide"
                    elif 'zanzibar' in content.lower():
                        return "Zanzibar Guide"
                return "Travel Guide"

            # Remove extension for display
            for ext in ['.pdf', '.docx', '.doc', '.txt', '.md', '.html']:
                if filename.lower().endswith(ext):
                    filename = filename[:-len(ext)]
                    break

            # Clean up underscores and format nicely
            filename = filename.replace('_', ' ').replace('-', ' ')

            # Title case but preserve acronyms
            words = filename.split()
            cleaned_words = []
            for word in words:
                if word.isupper() and len(word) <= 4:  # Preserve short acronyms
                    cleaned_words.append(word)
                else:
                    cleaned_words.append(word.title())

            return ' '.join(cleaned_words) if cleaned_words else "Knowledge Base"

        return source if source else "Knowledge Base"

    def _clean_content(self, content: str) -> str:
        """Clean document content for better context"""
        if not content:
            return ""

        # Remove excessive whitespace
        content = ' '.join(content.split())

        # If starts with lowercase or partial word, try to find sentence start
        if content and content[0].islower():
            # Find first capital letter that starts a sentence
            for i, char in enumerate(content):
                if char.isupper() and (i == 0 or content[i-1] in '. !?\n'):
                    content = content[i:]
                    break

        return content.strip()

    def _build_context(self, results: List[Dict], max_chars: int) -> str:
        """Build context string from search results"""
        context_parts = []
        total_chars = 0

        for i, r in enumerate(results):
            content = r.get('content', '')
            source = self._clean_source_name(r.get('source', 'Document'), r)

            # Clean the content
            content = self._clean_content(content)

            if not content:
                continue

            # Truncate individual documents if too long
            if len(content) > 1200:
                # Try to end at a sentence
                truncated = content[:1200]
                last_period = truncated.rfind('.')
                if last_period > 800:
                    content = truncated[:last_period + 1]
                else:
                    content = truncated + "..."

            part = f"[Source: {source}]\n{content}"

            if total_chars + len(part) > max_chars:
                break

            context_parts.append(part)
            total_chars += len(part)

        return "\n\n---\n\n".join(context_parts)

    def _call_llm(self, question: str, context: str, query_type: str = "general") -> str:
        """Call GPT-4o-mini to synthesize response"""
        # Build system prompt with query-specific guidance
        query_guidance = QUERY_TYPE_PROMPTS.get(query_type, QUERY_TYPE_PROMPTS["general"])
        full_system_prompt = SYSTEM_PROMPT + "\n" + query_guidance

        user_prompt = f"""Question: {question}

Context from knowledge base:
{context}

Provide a helpful, natural response using the information above. If the context doesn't contain relevant information, honestly acknowledge that."""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": full_system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.6,  # Balanced for natural but accurate
            max_tokens=500,
            timeout=15.0  # Generous timeout
        )

        return response.choices[0].message.content

    def _fallback_response(self, question: str, results: List[Dict]) -> Dict[str, Any]:
        """Fallback when LLM unavailable - return improved formatted results"""
        if not results:
            return self._no_results_response(question)

        # Build a structured response from top results
        content_parts = []
        seen_content = set()  # Avoid duplicates

        for r in results[:3]:
            content = r.get('content', '').strip()
            if content:
                # Clean the content
                content = self._clean_content(content)

                # Skip if we've seen very similar content
                content_sig = content[:100].lower()
                if content_sig in seen_content:
                    continue
                seen_content.add(content_sig)

                # Take first 400 chars but try to end at sentence
                if len(content) > 400:
                    end_pos = content[:400].rfind('.')
                    if end_pos > 200:
                        content = content[:end_pos + 1]
                    else:
                        content = content[:400] + "..."

                content_parts.append(content)

        if not content_parts:
            return self._no_results_response(question)

        combined = "\n\n".join(content_parts)
        answer = f"Here's what I found for you:\n\n{combined}\n\nWant me to dig deeper into any of these, or help you find something specific?"

        return {
            'answer': answer,
            'sources': [
                {'filename': self._clean_source_name(r.get('source', ''), r), 'score': r.get('score', 0)}
                for r in results[:3]
            ],
            'method': 'fallback'
        }

    def _no_results_response(self, question: str) -> Dict[str, Any]:
        """Graceful handling when no relevant documents found"""
        answer = (
            "Hmm, I don't have specific details on that in my knowledge base right now. "
            "A few things that might help:\n\n"
            "- Try asking in a different way - sometimes different keywords work better\n"
            "- For specific rates or availability, the pricing system might have what you need\n"
            "- If you're looking for a particular property, I can help you find similar options\n\n"
            "What else can I help you with?"
        )
        return {
            'answer': answer,
            'sources': [],
            'method': 'no_results'
        }


# Singleton instance
_rag_service = None


def get_rag_service() -> RAGResponseService:
    """Get singleton RAG service instance"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGResponseService()
    return _rag_service


def generate_rag_response(
    question: str,
    search_results: List[Dict[str, Any]],
    query_type: str = "general"
) -> Dict[str, Any]:
    """Convenience function for generating RAG responses"""
    service = get_rag_service()
    return service.generate_response(question, search_results, query_type)


if __name__ == "__main__":
    # Test with mock results
    print("RAG Response Service Test")
    print("=" * 60)

    mock_results = [
        {
            'content': 'Solana Beach is a stunning 5-star resort on the east coast of Mauritius. The property features 117 sea-facing rooms with private balconies and contemporary design. Guests enjoy personalized service, multiple restaurants, and direct beach access.',
            'score': 0.85,
            'source': '/var/folders/c2/tmp123/hotels.pdf'
        },
        {
            'content': 'For an all-inclusive luxury experience, Constance Belle Mare offers world-class amenities. The resort has 2 championship golf courses, 5 restaurants, and a renowned spa. Rates start from $450 per night.',
            'score': 0.78,
            'source': 'mauritius_luxury.md'
        }
    ]

    service = RAGResponseService()
    print(f"\nService status: {service.get_status()}")

    result = service.generate_response(
        "What luxury hotels do you have in Mauritius?",
        mock_results,
        query_type="hotel_info"
    )

    print(f"\nMethod: {result['method']}")
    print(f"Query Type: {result.get('query_type', 'N/A')}")
    print(f"\nAnswer:\n{result['answer']}")
    print(f"\nSources: {result['sources']}")
