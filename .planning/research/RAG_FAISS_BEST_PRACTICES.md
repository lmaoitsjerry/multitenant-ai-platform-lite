# RAG with FAISS Best Practices: Natural Conversational Responses

**Researched:** 2026-01-17
**Domain:** RAG (Retrieval-Augmented Generation) with FAISS vector search
**Confidence:** HIGH (verified with multiple authoritative sources)
**Context:** Helpdesk system with 98,086 documents, GPT-4o-mini synthesis, travel/hotel content

---

## Executive Summary

This research addresses why the current helpdesk RAG system returns raw document dumps instead of natural conversational responses, and provides actionable recommendations for improvement.

**Key findings:**
1. The current implementation has solid foundations but the fallback mode ("Based on our knowledge base...") triggers when OpenAI API calls fail silently
2. Document chunking and retrieval parameters need optimization for travel content
3. Prompt engineering can be significantly improved for natural responses
4. Re-ranking and MMR would dramatically improve response quality

**Primary recommendation:** Implement robust error handling with explicit logging, optimize chunk retrieval with MMR diversity, and enhance prompt engineering for conversational synthesis.

---

## Part 1: Why LLM Synthesis Might Be Failing

### Current System Analysis

The codebase shows the following flow:
```
User Question
    |
    v
FAISS search_with_context() -> top 8 docs, min_score 0.3
    |
    v
RAGResponseService.generate_response()
    |
    v
[IF no OpenAI client] --> _fallback_response() --> "Based on our knowledge base..."
[IF exception]        --> _fallback_response() --> "Based on our knowledge base..."
[IF success]          --> Natural response via GPT-4o-mini
```

### Common Failure Points (HIGH confidence)

#### 1. Missing or Invalid API Key

**Location:** `src/services/rag_response_service.py` lines 18-28

```python
# Current implementation
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
```

**Problem:** If `OPENAI_API_KEY` is not set or invalid, `self.client` returns `None` silently, triggering fallback.

**Diagnosis:**
```bash
# Check if API key is set
echo $OPENAI_API_KEY

# Test API key validity
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

**Recommended fix:**
```python
def __init__(self):
    self.openai_api_key = os.getenv('OPENAI_API_KEY')
    self._client = None

    if not self.openai_api_key:
        logger.warning("OPENAI_API_KEY not set - RAG synthesis will use fallback mode")
    elif not self.openai_api_key.startswith('sk-'):
        logger.warning("OPENAI_API_KEY appears invalid (should start with 'sk-')")

@property
def client(self):
    if self._client is None:
        if not self.openai_api_key:
            logger.error("Cannot create OpenAI client: OPENAI_API_KEY not set")
            return None
        try:
            import openai
            self._client = openai.OpenAI(api_key=self.openai_api_key)
            # Verify client works with a lightweight call
            self._client.models.list()
            logger.info("OpenAI client initialized successfully")
        except openai.AuthenticationError as e:
            logger.error(f"OpenAI authentication failed: {e}")
            self._client = None
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self._client = None
    return self._client
```

#### 2. Timeout Issues

**Location:** `src/services/rag_response_service.py` line 157

```python
response = self.client.chat.completions.create(
    ...
    timeout=8.0  # Stay under 3s total target
)
```

**Problem:** 8-second timeout may be insufficient for complex queries with large context. The comment says "Stay under 3s total target" but timeout is 8s - this is a disconnect.

**Recommended fix:**
```python
# Use httpx timeout configuration for better control
response = self.client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[...],
    temperature=0.7,
    max_tokens=500,
    timeout=httpx.Timeout(
        connect=2.0,    # Connection timeout
        read=10.0,      # Read timeout (increased for synthesis)
        write=5.0,      # Write timeout
        pool=5.0        # Pool timeout
    )
)
```

#### 3. Rate Limiting (429 Errors)

**Problem:** No retry logic for rate limit errors.

**Recommended fix with exponential backoff:**
```python
import time
from openai import RateLimitError, APIError

def _call_llm_with_retry(self, question: str, context: str, max_retries: int = 3) -> str:
    """Call GPT-4o-mini with retry logic for rate limits"""

    for attempt in range(max_retries):
        try:
            return self._call_llm(question, context)
        except RateLimitError as e:
            if attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1  # 1s, 3s, 5s
                logger.warning(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}")
                time.sleep(wait_time)
            else:
                logger.error(f"Rate limit exceeded after {max_retries} retries")
                raise
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
```

#### 4. Silent Exception Handling

**Location:** `src/services/rag_response_service.py` lines 70-72

```python
except Exception as e:
    logger.error(f"LLM synthesis failed: {e}")
    return self._fallback_response(question, search_results)
```

**Problem:** Generic exception catching hides the root cause. Need to log stack trace.

**Recommended fix:**
```python
except openai.AuthenticationError as e:
    logger.error(f"OpenAI authentication failed: {e}")
    return self._fallback_response(question, search_results, reason="auth_failed")
except openai.RateLimitError as e:
    logger.error(f"OpenAI rate limit exceeded: {e}")
    return self._fallback_response(question, search_results, reason="rate_limited")
except openai.APITimeoutError as e:
    logger.error(f"OpenAI request timed out: {e}")
    return self._fallback_response(question, search_results, reason="timeout")
except Exception as e:
    logger.error(f"LLM synthesis failed unexpectedly: {e}", exc_info=True)
    return self._fallback_response(question, search_results, reason="unknown_error")
```

---

## Part 2: Document Chunking Strategies

### Current State Analysis

The current system uses a pre-built FAISS index with 98,086 documents stored in GCS. The chunking was done during index creation and cannot be changed without rebuilding.

### Optimal Chunk Sizes (HIGH confidence)

Research consistently shows:

| Content Type | Optimal Chunk Size | Overlap |
|--------------|-------------------|---------|
| FAQ/Short answers | 128-256 tokens | 10-15% |
| Hotel descriptions | 256-512 tokens | 15-20% |
| Detailed guides | 512-1024 tokens | 20% |
| Travel itineraries | 512-768 tokens | 15-20% |

**For travel/hotel content specifically:**
- **Hotel listings:** 300-500 tokens (captures name, location, amenities, price range)
- **Destination guides:** 500-800 tokens (provides context without losing focus)
- **Policies/FAQs:** 150-300 tokens (precise answers)

### Chunking Strategies Comparison

#### 1. Fixed-Size Chunking (Simple, Current Likely Approach)
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,      # ~125 tokens
    chunk_overlap=50,    # 10% overlap
    separators=["\n\n", "\n", ". ", " "]
)
```
**Pros:** Simple, predictable
**Cons:** Can split mid-sentence, loses semantic boundaries

#### 2. Semantic Chunking (RECOMMENDED for rebuild)
```python
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings()
semantic_splitter = SemanticChunker(
    embeddings,
    breakpoint_threshold_type="percentile",
    breakpoint_threshold_amount=95
)
```
**Pros:** Respects semantic boundaries, better for natural responses
**Cons:** More expensive (requires embedding calls during chunking)

#### 3. Parent-Child Document Retrieval (Advanced)

Store both small chunks (for retrieval precision) and their parent documents (for context):

```python
from langchain.retrievers import ParentDocumentRetriever
from langchain.storage import InMemoryStore

# Small chunks for search
child_splitter = RecursiveCharacterTextSplitter(chunk_size=200)
# Larger parents for context
parent_splitter = RecursiveCharacterTextSplitter(chunk_size=1000)

store = InMemoryStore()
retriever = ParentDocumentRetriever(
    vectorstore=faiss_store,
    docstore=store,
    child_splitter=child_splitter,
    parent_splitter=parent_splitter,
)
```

**Use case:** Search on specific details, return full context for synthesis

### Travel/Hotel Content-Specific Recommendations

```python
# Recommended chunking configuration for travel content
TRAVEL_CHUNK_CONFIG = {
    "hotel_listings": {
        "chunk_size": 400,
        "chunk_overlap": 60,
        "separators": ["\n\n", "\n", "---", ". "],
        "metadata_fields": ["hotel_name", "location", "star_rating", "price_range"]
    },
    "destination_guides": {
        "chunk_size": 600,
        "chunk_overlap": 100,
        "separators": ["\n## ", "\n### ", "\n\n", "\n"],
        "metadata_fields": ["destination", "category", "season"]
    },
    "policies": {
        "chunk_size": 250,
        "chunk_overlap": 25,
        "separators": ["\n\n", "\n", ". "],
        "metadata_fields": ["policy_type", "effective_date"]
    }
}
```

---

## Part 3: Retrieval Optimization

### Current Implementation Analysis

```python
# Current: src/services/faiss_helpdesk_service.py
def search_with_context(self, query: str, top_k: int = 8, min_score: float = 0.3):
    all_results = self.search(query, top_k=top_k)
    filtered_results = [r for r in all_results if r['score'] >= min_score]
    # Returns minimum 3 results even if below threshold
```

**Issues identified:**
1. No re-ranking (relies solely on FAISS L2 distance)
2. No diversity consideration (top results may be redundant)
3. Fixed k value regardless of query complexity
4. Score threshold too low (0.3) may include irrelevant content

### Optimal K Values (HIGH confidence)

| Use Case | Initial K | After Filtering | Rationale |
|----------|-----------|-----------------|-----------|
| Simple factual query | 5-10 | 3-5 | Precision matters |
| Complex multi-part query | 15-20 | 8-12 | Need broader context |
| Comparison/options query | 10-15 | 5-8 | Diversity matters |
| Travel/hotel search | 10-15 | 5-8 | Multiple options needed |

**Recommended dynamic K:**
```python
def determine_k(query: str) -> tuple[int, int]:
    """Determine retrieval K based on query characteristics"""
    query_lower = query.lower()

    # Multi-hotel queries need more results
    if any(word in query_lower for word in ['hotels', 'options', 'compare', 'recommend']):
        return 15, 8  # fetch 15, use top 8

    # Simple factual queries
    if any(word in query_lower for word in ['what is', 'how to', 'when', 'where']):
        return 8, 4  # fetch 8, use top 4

    # Default
    return 10, 5
```

### Re-ranking Implementation (RECOMMENDED)

Add a cross-encoder re-ranker after FAISS retrieval:

```python
from sentence_transformers import CrossEncoder

class ReRanker:
    def __init__(self):
        # ms-marco-MiniLM-L-6-v2 is fast and effective
        self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')

    def rerank(self, query: str, results: list, top_k: int = 5) -> list:
        """Re-rank results using cross-encoder"""
        if not results:
            return results

        # Prepare pairs for scoring
        pairs = [(query, r['content']) for r in results]

        # Get cross-encoder scores
        scores = self.model.predict(pairs)

        # Add rerank scores and sort
        for i, result in enumerate(results):
            result['rerank_score'] = float(scores[i])

        reranked = sorted(results, key=lambda x: x['rerank_score'], reverse=True)
        return reranked[:top_k]
```

**Integration into current system:**
```python
def search_with_context(self, query: str, top_k: int = 8, min_score: float = 0.3):
    # Fetch more candidates for re-ranking
    candidates = self.search(query, top_k=top_k * 2)  # 16 candidates

    if not candidates:
        return []

    # Re-rank
    reranker = get_reranker()  # Singleton
    reranked = reranker.rerank(query, candidates, top_k=top_k)

    # Filter by score
    filtered = [r for r in reranked if r['score'] >= min_score]
    return filtered if len(filtered) >= 3 else reranked[:3]
```

### MMR (Maximum Marginal Relevance) for Diversity

Critical for hotel/travel queries where users want OPTIONS, not duplicates:

```python
import numpy as np

def mmr_rerank(
    query_embedding: np.ndarray,
    doc_embeddings: np.ndarray,
    documents: list,
    lambda_param: float = 0.7,  # 0.7 = relevance-leaning
    top_k: int = 5
) -> list:
    """
    MMR: Balance relevance and diversity

    lambda_param:
        1.0 = pure relevance (no diversity)
        0.0 = pure diversity (ignore relevance)
        0.5-0.7 = recommended for travel content
    """
    selected_indices = []
    remaining_indices = list(range(len(documents)))

    # Similarity to query (relevance)
    query_similarities = np.dot(doc_embeddings, query_embedding)

    for _ in range(min(top_k, len(documents))):
        if not remaining_indices:
            break

        mmr_scores = []
        for idx in remaining_indices:
            relevance = query_similarities[idx]

            # Diversity: max similarity to already selected docs
            if selected_indices:
                diversity_penalty = max(
                    np.dot(doc_embeddings[idx], doc_embeddings[sel_idx])
                    for sel_idx in selected_indices
                )
            else:
                diversity_penalty = 0

            mmr = lambda_param * relevance - (1 - lambda_param) * diversity_penalty
            mmr_scores.append((idx, mmr))

        # Select highest MMR
        best_idx = max(mmr_scores, key=lambda x: x[1])[0]
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)

    return [documents[i] for i in selected_indices]
```

**Recommended lambda values for travel:**
- Hotel recommendations: 0.6 (more diversity)
- Specific hotel queries: 0.8 (more relevance)
- Destination info: 0.7 (balanced)

### Hybrid Search (Vector + Keyword)

Combine FAISS with BM25 for better recall:

```python
from rank_bm25 import BM25Okapi

class HybridSearcher:
    def __init__(self, faiss_service, documents):
        self.faiss = faiss_service
        self.documents = documents

        # Build BM25 index
        tokenized = [doc['content'].lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized)

    def search(self, query: str, top_k: int = 10, alpha: float = 0.5) -> list:
        """
        Hybrid search combining vector and keyword
        alpha: 0.5 = equal weight, >0.5 = favor vector, <0.5 = favor keyword
        """
        # Vector search
        vector_results = self.faiss.search(query, top_k=top_k * 2)

        # BM25 search
        tokenized_query = query.lower().split()
        bm25_scores = self.bm25.get_scores(tokenized_query)

        # Normalize and combine scores
        combined = {}
        for r in vector_results:
            doc_id = r['index']
            combined[doc_id] = {
                'document': r,
                'vector_score': r['score'],
                'bm25_score': bm25_scores[doc_id] if doc_id < len(bm25_scores) else 0
            }

        # Rank by combined score
        for doc_id, scores in combined.items():
            scores['combined'] = (
                alpha * scores['vector_score'] +
                (1 - alpha) * self._normalize(scores['bm25_score'], bm25_scores)
            )

        ranked = sorted(combined.values(), key=lambda x: x['combined'], reverse=True)
        return [r['document'] for r in ranked[:top_k]]
```

---

## Part 4: Response Synthesis Best Practices

### Current Prompt Analysis

**Location:** `src/services/rag_response_service.py` lines 125-147

The current system prompt is reasonable but has room for improvement:

```python
# Current
system_prompt = """You are a helpful travel assistant for a property management platform..."""

# Issues:
# 1. Generic "travel assistant" - should be more specific
# 2. Guidelines mixed with prohibitions
# 3. No structured output guidance
# 4. No examples of good responses
```

### Optimized System Prompt (RECOMMENDED)

```python
SYSTEM_PROMPT = """You are a knowledgeable travel consultant for a luxury travel agency. Your role is to help travel agents find information about hotels, destinations, and travel arrangements.

## Response Style
- Write conversationally, as if speaking to a colleague
- Be warm but professional
- Get to the point quickly - agents are busy
- Use specific names, prices, and details from the context
- When listing hotels, explain WHY each might suit the client's needs

## Response Structure
For hotel queries:
1. Lead with the best match and why
2. Offer 2-3 alternatives with brief differentiators
3. End with an actionable next step

For information queries:
1. Answer the question directly
2. Add relevant context or tips
3. Offer to elaborate if needed

## Handling Limitations
- If context is incomplete, say what you DO know and what's missing
- Never invent details not in the provided context
- If truly no relevant info, suggest how the agent might find it

## Examples of Good Responses

QUESTION: "What hotels in Maldives have overwater villas?"

GOOD: "For overwater villas in the Maldives, Soneva Fushi is an excellent choice - they offer spacious villas starting at $1,200/night with private pools and butler service. The Conrad Maldives is a great family-friendly alternative with two-bedroom overwater options from $800/night. Both have excellent availability for the dates you're likely looking at. Want me to pull specific rates for a particular date range?"

BAD: "Based on the documents I found, there are hotels in the Maldives with overwater villas. Soneva Fushi has overwater villas. Conrad Maldives has overwater villas. These are the options available."

## Do NOT
- Start with "Based on the context..." or "According to the documents..."
- List information without interpretation
- Use bullet points for everything
- Give generic travel advice not from the context"""
```

### User Prompt Template

```python
USER_PROMPT_TEMPLATE = """QUESTION: {question}

CONTEXT FROM KNOWLEDGE BASE:
{context}

---
Answer the question naturally using the information above. If multiple options are relevant, help the agent understand which might be best for different client needs."""
```

### Context Window Management

**Current:** max_context_chars = 6000 (~1500 tokens)

**Recommended approach:**
```python
def build_context(
    results: list,
    max_tokens: int = 2000,  # Reserve ~2500 for response
    chars_per_token: float = 4.0
) -> str:
    """
    Build context with intelligent truncation
    """
    max_chars = int(max_tokens * chars_per_token)

    # Prioritize by score
    results = sorted(results, key=lambda x: x.get('rerank_score', x.get('score', 0)), reverse=True)

    context_parts = []
    total_chars = 0

    for i, r in enumerate(results):
        content = r.get('content', '').strip()
        source = r.get('source', 'Unknown')

        # Summarize long documents instead of truncating
        if len(content) > 800:
            content = summarize_chunk(content, max_length=600)

        part = f"[{i+1}. {source}]\n{content}"

        if total_chars + len(part) > max_chars:
            # Try to fit partial if near limit
            remaining = max_chars - total_chars - 50
            if remaining > 200 and i < 3:  # Always try to include top 3
                part = f"[{i+1}. {source}]\n{content[:remaining]}..."
                context_parts.append(part)
            break

        context_parts.append(part)
        total_chars += len(part)

    return "\n\n".join(context_parts)
```

### Temperature and Generation Parameters

**Current:** temperature=0.7, max_tokens=500

**Recommended settings by query type:**

| Query Type | Temperature | Max Tokens | Rationale |
|------------|-------------|------------|-----------|
| Factual (prices, dates) | 0.2-0.3 | 300 | Precision needed |
| Recommendations | 0.5-0.7 | 500 | Some creativity |
| Descriptions | 0.6-0.8 | 600 | More natural flow |
| Troubleshooting | 0.3-0.4 | 400 | Accuracy matters |

```python
def get_generation_params(question: str) -> dict:
    """Dynamic generation parameters based on query type"""
    q_lower = question.lower()

    if any(w in q_lower for w in ['price', 'cost', 'rate', 'how much', 'when']):
        return {"temperature": 0.3, "max_tokens": 300}

    if any(w in q_lower for w in ['recommend', 'suggest', 'best', 'which']):
        return {"temperature": 0.6, "max_tokens": 500}

    if any(w in q_lower for w in ['describe', 'tell me about', 'what is']):
        return {"temperature": 0.7, "max_tokens": 600}

    return {"temperature": 0.5, "max_tokens": 450}
```

### Source Attribution Without Breaking Flow

**Bad:**
```
According to document soneva_fushi.pdf (relevance: 0.85), Soneva Fushi offers...
```

**Good:**
```
Soneva Fushi offers luxury overwater villas starting at $1,200/night.
[Sources displayed separately in UI]
```

The current implementation handles this well by returning sources separately in the response dict.

---

## Part 5: Travel/Hotel Content Recommendations

### Presenting Multiple Hotels Naturally

```python
HOTEL_COMPARISON_PROMPT = """When presenting multiple hotels, structure your response as:

1. **Lead recommendation** - The single best match with 2-3 sentences explaining why

2. **Strong alternatives** - 1-2 other options with differentiators:
   - "For a more intimate experience..."
   - "If budget flexibility exists..."
   - "For families specifically..."

3. **Quick comparison** (only if asked or >3 options):
   Brief table or comparison of key factors

4. **Next step** - What the agent should do next

Example:
"For an overwater experience in the Maldives, I'd start with **Soneva Fushi** - their villas offer exceptional privacy with personal pools and butler service, starting at $1,200/night.

If your clients prefer a more social atmosphere, the **Conrad Maldives** has a fantastic main restaurant and spa, plus two-bedroom options perfect for families at $800/night.

For the ultimate splurge, **One&Only Reethi Rah** has the largest villas in the Maldives, though you're looking at $2,500+ per night.

Would you like me to check availability for specific dates, or would more details on any of these help?"
"""
```

### Information Structure for Conversational Responses

```python
RESPONSE_STRUCTURE = {
    "hotel_query": {
        "components": [
            "name_and_standout_feature",
            "location_context",
            "price_range",
            "ideal_guest_profile",
            "booking_consideration"
        ],
        "example": "Soneva Fushi stands out for its eco-luxury approach, located on a private island in Baa Atoll. Rates from $1,200/night make it mid-to-high range for Maldives. Perfect for couples wanting seclusion. Worth noting they often book out 6 months ahead for peak season."
    },
    "destination_query": {
        "components": [
            "quick_overview",
            "best_for",
            "timing_tip",
            "practical_note"
        ],
        "example": "Zanzibar blends pristine beaches with Stone Town's UNESCO heritage. Best for clients wanting beach + culture. Dry season (June-October) is ideal. Direct flights from Nairobi make it easy to combine with Kenya safari."
    }
}
```

### Balancing Detail with Readability

**Principle:** Answer the question asked, then offer depth.

```python
# Bad: Information dump
"""
Soneva Fushi is a luxury resort. It has 63 villas. The villas range from
one bedroom to nine bedrooms. Prices start at $1,200. It is located in
Baa Atoll. Baa Atoll is a UNESCO Biosphere Reserve. The resort was
founded in 1995. It has a no-shoes policy. There are 7 restaurants...
"""

# Good: Relevant answer with optional depth
"""
Soneva Fushi is your top pick for eco-conscious luxury in the Maldives -
think private island, no shoes, and serious sustainability creds. Villas
start at $1,200/night for one-bedrooms, with larger options for families
or groups.

The location in Baa Atoll is a UNESCO Biosphere Reserve, which means
exceptional snorkeling and diving right from the villa.

Want me to go deeper on dining options, spa facilities, or family amenities?
"""
```

---

## Part 6: Implementation Recommendations

### Priority 1: Fix API Key and Error Handling (Immediate)

```python
# Enhanced RAGResponseService with proper error handling
class RAGResponseService:
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self._client = None
        self._api_status = self._validate_api_key()

    def _validate_api_key(self) -> dict:
        """Validate API key on startup"""
        if not self.openai_api_key:
            logger.error("OPENAI_API_KEY environment variable not set")
            return {"valid": False, "reason": "not_set"}

        if not self.openai_api_key.startswith('sk-'):
            logger.error("OPENAI_API_KEY format appears invalid")
            return {"valid": False, "reason": "invalid_format"}

        # Test with lightweight call
        try:
            import openai
            client = openai.OpenAI(api_key=self.openai_api_key)
            client.models.list()  # Quick validation
            logger.info("OpenAI API key validated successfully")
            return {"valid": True, "reason": None}
        except openai.AuthenticationError:
            logger.error("OpenAI API key authentication failed")
            return {"valid": False, "reason": "auth_failed"}
        except Exception as e:
            logger.warning(f"OpenAI API key validation warning: {e}")
            return {"valid": True, "reason": "validation_skipped"}

    def get_status(self) -> dict:
        """Return service status for health checks"""
        return {
            "api_key_configured": bool(self.openai_api_key),
            "api_status": self._api_status,
            "synthesis_available": self._api_status.get("valid", False)
        }
```

### Priority 2: Add Re-ranking (High Impact)

```python
# Add to src/services/reranker_service.py
from functools import lru_cache
from sentence_transformers import CrossEncoder
import logging

logger = logging.getLogger(__name__)

class ReRankerService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        try:
            self.model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            self._initialized = True
            logger.info("ReRanker service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize reranker: {e}")
            self.model = None
            self._initialized = True

    def rerank(self, query: str, results: list, top_k: int = 5) -> list:
        if not self.model or not results:
            return results[:top_k]

        pairs = [(query, r.get('content', '')) for r in results]
        scores = self.model.predict(pairs)

        for i, result in enumerate(results):
            result['rerank_score'] = float(scores[i])

        return sorted(results, key=lambda x: x['rerank_score'], reverse=True)[:top_k]

@lru_cache(maxsize=1)
def get_reranker() -> ReRankerService:
    return ReRankerService()
```

### Priority 3: Improve Prompt Engineering (Medium Effort, High Impact)

Update `src/services/rag_response_service.py`:

```python
SYSTEM_PROMPT = """You are a knowledgeable travel consultant helping travel agents find information.

RESPONSE PRINCIPLES:
1. Lead with the direct answer, then elaborate
2. Use specific details (names, prices, features) from the context
3. When multiple options exist, explain what makes each different
4. End with a helpful next step or offer to elaborate

STYLE:
- Conversational but professional
- Confident about what's in the context
- Honest about gaps or limitations
- Never robotic or list-heavy

NEVER:
- Start with "Based on the context..." or "According to..."
- Invent details not in the provided information
- Give generic advice not supported by the context"""

def _call_llm(self, question: str, context: str) -> str:
    # Get dynamic parameters
    params = self._get_generation_params(question)

    user_prompt = f"""Question: {question}

Information from knowledge base:
{context}

Provide a helpful, natural response. If multiple options are relevant, explain what makes each unique."""

    response = self.client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=params['temperature'],
        max_tokens=params['max_tokens'],
        timeout=10.0
    )

    return response.choices[0].message.content

def _get_generation_params(self, question: str) -> dict:
    q = question.lower()

    if any(w in q for w in ['price', 'cost', 'rate', 'how much']):
        return {"temperature": 0.3, "max_tokens": 350}
    if any(w in q for w in ['recommend', 'suggest', 'best', 'options']):
        return {"temperature": 0.6, "max_tokens": 500}

    return {"temperature": 0.5, "max_tokens": 450}
```

### Priority 4: Add Health Check Endpoint

```python
# Add to src/api/helpdesk_routes.py
@helpdesk_router.get("/health")
async def helpdesk_health():
    """Health check including RAG service status"""
    from src.services.faiss_helpdesk_service import get_faiss_helpdesk_service
    from src.services.rag_response_service import get_rag_service

    faiss = get_faiss_helpdesk_service()
    rag = get_rag_service()

    return {
        "status": "healthy",
        "faiss": faiss.get_status(),
        "rag": rag.get_status() if hasattr(rag, 'get_status') else {"unknown": True},
        "synthesis_mode": "llm" if rag.client else "fallback"
    }
```

---

## Verification Checklist

Before deploying improvements:

- [ ] OPENAI_API_KEY is set and valid
- [ ] Health endpoint confirms synthesis_mode is "llm" not "fallback"
- [ ] Test queries produce natural responses (not "Based on our knowledge base...")
- [ ] Timing stays under 3s target (search + synthesis)
- [ ] Multiple hotel queries return diverse options
- [ ] Fallback still works gracefully if API fails

---

## Sources

### Primary (HIGH confidence)
- [Prompt Engineering Guide - RAG](https://www.promptingguide.ai/research/rag)
- [AWS - What is RAG](https://aws.amazon.com/what-is/retrieval-augmented-generation/)
- [Weaviate - Chunking Strategies](https://weaviate.io/blog/chunking-strategies-for-rag)
- [Firecrawl - Best Chunking Strategies 2025](https://www.firecrawl.dev/blog/best-chunking-strategies-rag-2025)
- [Superlinked - Optimizing RAG with Hybrid Search & Reranking](https://superlinked.com/vectorhub/articles/optimizing-rag-with-hybrid-search-reranking)
- [Qdrant - MMR Diversity-Aware Reranking](https://qdrant.tech/blog/mmr-diversity-aware-reranking/)
- [OpenAI Developer Community - Optimal Temperature for RAG](https://community.openai.com/t/optimal-temperature-setting-for-llm-generation-in-rag-model/1030531)
- [ZeroEntropy - Best Reranking Model 2025](https://www.zeroentropy.dev/articles/ultimate-guide-to-choosing-the-best-reranking-model-in-2025)

### Secondary (MEDIUM confidence)
- [Neo4j - Advanced RAG Techniques](https://neo4j.com/blog/genai/advanced-rag-techniques/)
- [Agentive AI - RAG Chatbots for Hotels](https://agentiveaiq.com/listicles/5-best-rag-chatbots-for-hotels)
- [LangCopilot - Document Chunking Strategies](https://langcopilot.com/posts/2025-10-11-document-chunking-for-rag-practical-guide)
- [Machine Learning Plus - Optimizing RAG Chunk Size](https://machinelearningplus.com/gen-ai/optimizing-rag-chunk-size-your-definitive-guide-to-better-retrieval-accuracy/)

### Codebase Analysis
- `src/services/rag_response_service.py` - Current RAG synthesis implementation
- `src/services/faiss_helpdesk_service.py` - FAISS search implementation
- `src/api/helpdesk_routes.py` - Helpdesk API routes

---

## Metadata

**Confidence breakdown:**
- Error handling recommendations: HIGH - based on OpenAI docs and common patterns
- Chunking strategies: HIGH - multiple research sources agree
- Retrieval optimization: HIGH - well-documented best practices
- Prompt engineering: MEDIUM - effective patterns but requires tuning
- Travel-specific recommendations: MEDIUM - derived from general principles

**Research date:** 2026-01-17
**Valid until:** 2026-04-17 (3 months for stable RAG patterns)
