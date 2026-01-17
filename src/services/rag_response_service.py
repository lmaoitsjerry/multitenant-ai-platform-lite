"""
RAG Response Service - Natural Language Synthesis

Transforms FAISS search results into conversational, helpful responses
using GPT-4o-mini. Handles unknown questions gracefully.
"""

import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class RAGResponseService:
    """Synthesize natural responses from knowledge base search results"""

    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self._client = None

    @property
    def client(self):
        """Lazy-load OpenAI client"""
        if self._client is None and self.openai_api_key:
            import openai
            self._client = openai.OpenAI(api_key=self.openai_api_key)
        return self._client

    def generate_response(
        self,
        question: str,
        search_results: List[Dict[str, Any]],
        max_context_chars: int = 6000
    ) -> Dict[str, Any]:
        """
        Generate a natural response from search results.

        Args:
            question: User's original question
            search_results: List of dicts with 'content', 'score', 'source'
            max_context_chars: Maximum characters of context to include

        Returns:
            Dict with 'answer', 'sources', 'method' ('rag' or 'fallback')
        """
        # No API key - return structured fallback
        if not self.client:
            logger.warning("No OpenAI API key, cannot synthesize RAG response")
            return self._fallback_response(question, search_results)

        # No search results - handle gracefully
        if not search_results:
            return self._no_results_response(question)

        # Build context from search results
        context = self._build_context(search_results, max_context_chars)

        # Generate response
        try:
            answer = self._call_llm(question, context)
            return {
                'answer': answer,
                'sources': [
                    {'filename': self._clean_source_name(r.get('source', '')), 'score': r.get('score', 0)}
                    for r in search_results[:5]  # Top 5 sources
                ],
                'method': 'rag'
            }
        except Exception as e:
            logger.error(f"LLM synthesis failed: {e}")
            return self._fallback_response(question, search_results)

    def _clean_source_name(self, source: str) -> str:
        """Clean up source names - convert temp file paths to friendly names"""
        if not source:
            return "Knowledge Base"

        # Extract filename from path
        if '/' in source or '\\' in source:
            # Get just the filename
            filename = source.replace('\\', '/').split('/')[-1]

            # Remove temp prefixes (e.g., tmpvz1yjphh_)
            if filename.startswith('tmp') or '/tmp' in source or '\\tmp' in source or 'Temp' in source:
                return "Knowledge Base Document"

            # Remove extension for display
            for ext in ['.pdf', '.docx', '.doc', '.txt', '.md']:
                if filename.lower().endswith(ext):
                    filename = filename[:-len(ext)]
                    break

            # Clean up underscores and format nicely
            filename = filename.replace('_', ' ').replace('-', ' ')
            return filename.title() if filename else "Knowledge Base"

        return source if source else "Knowledge Base"

    def _build_context(self, results: List[Dict], max_chars: int) -> str:
        """Build context string from search results"""
        context_parts = []
        total_chars = 0

        for i, r in enumerate(results):
            content = r.get('content', '')
            source = r.get('source', 'Document')

            # Truncate individual documents if too long
            if len(content) > 1500:
                content = content[:1500] + "..."

            part = f"[Source: {source}]\n{content}"

            if total_chars + len(part) > max_chars:
                break

            context_parts.append(part)
            total_chars += len(part)

        return "\n\n---\n\n".join(context_parts)

    def _call_llm(self, question: str, context: str) -> str:
        """Call GPT-4o-mini to synthesize response"""
        system_prompt = """You are a helpful travel assistant for a property management platform. Your job is to answer questions using ONLY the provided context from the knowledge base.

Guidelines:
1. Be conversational and friendly, not robotic or list-like
2. Include SPECIFIC details from the context (hotel names, prices, features, locations)
3. If the context doesn't fully answer the question, acknowledge what you know and what's missing
4. If the context has NO relevant information, honestly say you don't have that information
5. Keep responses concise but informative (2-4 paragraphs max)
6. Use natural language, not bullet points unless listing options
7. If recommending properties, explain WHY they fit the query

DO NOT:
- Make up information not in the context
- Give generic travel advice not from the documents
- Use corporate jargon or robotic language
- Start with "Based on the context..." or similar meta-language"""

        user_prompt = f"""Question: {question}

Context from knowledge base:
{context}

Provide a helpful, natural response using the information above. If the context doesn't contain relevant information, honestly acknowledge that."""

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7,  # Natural variation
            max_tokens=500,
            timeout=8.0  # Stay under 3s total target
        )

        return response.choices[0].message.content

    def _fallback_response(self, question: str, results: List[Dict]) -> Dict[str, Any]:
        """Fallback when LLM unavailable - return formatted results"""
        if not results:
            return self._no_results_response(question)

        # Build a more structured response from search results
        # Extract key info instead of raw dump
        content_parts = []
        for r in results[:3]:
            content = r.get('content', '').strip()
            if content:
                # Clean up the content - take first 400 chars but try to end at sentence
                if len(content) > 400:
                    end_pos = content[:400].rfind('.')
                    if end_pos > 200:
                        content = content[:end_pos + 1]
                    else:
                        content = content[:400] + "..."
                content_parts.append(content)

        combined = "\n\n".join(content_parts)
        answer = f"Based on our knowledge base:\n\n{combined}\n\nWould you like more details on any of these topics?"

        return {
            'answer': answer,
            'sources': [
                {'filename': self._clean_source_name(r.get('source', '')), 'score': r.get('score', 0)}
                for r in results[:3]
            ],
            'method': 'fallback'
        }

    def _no_results_response(self, question: str) -> Dict[str, Any]:
        """Graceful handling when no relevant documents found"""
        answer = (
            "I don't have specific information about that in my knowledge base. "
            "This could be because:\n\n"
            "- The topic isn't covered in our documentation yet\n"
            "- Try rephrasing your question with different keywords\n"
            "- For specific property or rate questions, the information might be in our pricing system instead\n\n"
            "Is there something else I can help you with, or would you like me to search for related topics?"
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


def generate_rag_response(question: str, search_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Convenience function for generating RAG responses"""
    service = get_rag_service()
    return service.generate_response(question, search_results)


if __name__ == "__main__":
    # Test with mock results
    mock_results = [
        {'content': 'The Maldives offers luxury overwater villas at Soneva Fushi starting at $1,200/night. Features include private pools, butler service, and direct lagoon access.', 'score': 0.85, 'source': 'maldives_hotels.md'},
        {'content': 'For families, Conrad Maldives has a kids club and two-bedroom villas. Rates from $800/night with meal plans available.', 'score': 0.78, 'source': 'maldives_family.md'}
    ]

    service = RAGResponseService()
    result = service.generate_response("What hotels in Maldives have pools?", mock_results)
    print(f"Method: {result['method']}")
    print(f"Answer:\n{result['answer']}")
