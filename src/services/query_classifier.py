"""
Query Classifier - Intelligent Query Type Detection

Classifies user queries to optimize retrieval parameters and response generation.
Different query types benefit from different search strategies and response styles.
"""

import re
import logging
from enum import Enum
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries the helpdesk can handle"""
    HOTEL_INFO = "hotel_info"          # "What hotels in Zanzibar?"
    PRICING = "pricing"                 # "How much for 5 nights?"
    PLATFORM_HELP = "platform_help"     # "How do I create a quote?"
    DESTINATION_INFO = "destination"    # "Tell me about Maldives"
    COMPARISON = "comparison"           # "Compare luxury vs budget"
    BOOKING_PROCESS = "booking"         # "How to make a booking?"
    GENERAL = "general"                 # Everything else


class QueryClassifier:
    """
    Classify user queries to optimize retrieval and response generation.

    Uses pattern matching to identify query intent, then returns optimal
    search parameters for that query type.
    """

    # Patterns for each query type (regex patterns)
    PATTERNS = {
        QueryType.HOTEL_INFO: [
            r'\b(hotel|resort|property|properties|accommodation|stay|lodge|villa)\b',
            r'\b(luxury|5\s*star|4\s*star|boutique|beach|all.?inclusive)\b.*\b(hotel|resort|option)?\b',
            r'\bwhat\b.*\b(hotels?|resorts?|properties)\b',
            r'\bshow\b.*\b(hotels?|resorts?|options?)\b',
        ],
        QueryType.PRICING: [
            r'\b(price|cost|rate|how much|pricing|per night|per person|budget)\b',
            r'\b(R\d+|\$\d+|USD|ZAR|affordable|expensive|cheap)\b',
            r'\bwhat.*(cost|price)\b',
        ],
        QueryType.PLATFORM_HELP: [
            r'\b(how (do|can|to)|create|generate|send|make|use)\b.*\b(quote|invoice|client|booking)\b',
            r'\b(platform|system|dashboard|feature|button|page|setting)\b',
            r'\bhow (do i|can i|to)\b',
        ],
        QueryType.DESTINATION_INFO: [
            r'\b(tell me about|what.?s|describe|info|information about)\b',
            r'\b(zanzibar|maldives|mauritius|kenya|victoria falls|seychelles|tanzania|cape town|kruger)\b',
            r'\bbest time (to visit|for)\b',
            r'\bweather\b.*\b(in|at)\b',
        ],
        QueryType.COMPARISON: [
            r'\b(compare|comparison|versus|vs|difference|better|best)\b',
            r'\b(which|what).*(recommend|suggest|prefer|choose)\b',
            r'\bor\b.*(which|better)',
        ],
        QueryType.BOOKING_PROCESS: [
            r'\b(book|booking|reserve|reservation|confirm|confirmation)\b',
            r'\b(process|step|procedure|how to book)\b',
        ],
    }

    # Search parameters optimized for each query type
    SEARCH_PARAMS = {
        QueryType.HOTEL_INFO: {
            "k": 6,               # Return 6 diverse hotel options
            "fetch_k": 15,        # Fetch 15 for MMR diversity
            "lambda_mmr": 0.6,    # More diversity for options
            "use_rerank": True,
            "use_mmr": True,
        },
        QueryType.PRICING: {
            "k": 4,               # Fewer, more precise results
            "fetch_k": 10,
            "lambda_mmr": 0.8,    # More relevance for specific pricing
            "use_rerank": True,
            "use_mmr": False,
        },
        QueryType.PLATFORM_HELP: {
            "k": 3,               # Usually one right answer
            "fetch_k": 8,
            "lambda_mmr": 0.9,    # High relevance
            "use_rerank": False,  # Platform help is usually straightforward
            "use_mmr": False,
        },
        QueryType.DESTINATION_INFO: {
            "k": 5,               # Mix of info about destination
            "fetch_k": 15,
            "lambda_mmr": 0.5,    # Balance for varied info
            "use_rerank": True,
            "use_mmr": True,
        },
        QueryType.COMPARISON: {
            "k": 8,               # Need multiple options to compare
            "fetch_k": 20,
            "lambda_mmr": 0.4,    # High diversity for comparison
            "use_rerank": True,
            "use_mmr": True,
        },
        QueryType.BOOKING_PROCESS: {
            "k": 3,
            "fetch_k": 8,
            "lambda_mmr": 0.9,
            "use_rerank": False,
            "use_mmr": False,
        },
        QueryType.GENERAL: {
            "k": 5,
            "fetch_k": 12,
            "lambda_mmr": 0.7,
            "use_rerank": True,
            "use_mmr": True,
        },
    }

    # Generation parameters for each query type
    GENERATION_PARAMS = {
        QueryType.HOTEL_INFO: {
            "temperature": 0.6,
            "max_tokens": 500,
        },
        QueryType.PRICING: {
            "temperature": 0.3,   # Low temperature for factual accuracy
            "max_tokens": 350,
        },
        QueryType.PLATFORM_HELP: {
            "temperature": 0.4,
            "max_tokens": 400,
        },
        QueryType.DESTINATION_INFO: {
            "temperature": 0.7,   # More creative for descriptions
            "max_tokens": 500,
        },
        QueryType.COMPARISON: {
            "temperature": 0.5,
            "max_tokens": 600,    # Longer for comparisons
        },
        QueryType.BOOKING_PROCESS: {
            "temperature": 0.4,
            "max_tokens": 400,
        },
        QueryType.GENERAL: {
            "temperature": 0.5,
            "max_tokens": 450,
        },
    }

    def classify(self, query: str) -> Tuple[QueryType, float]:
        """
        Classify a query and return its type with confidence score.

        Args:
            query: User's question

        Returns:
            Tuple of (QueryType, confidence_score)
        """
        query_lower = query.lower()
        scores = {}

        for query_type, patterns in self.PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower, re.IGNORECASE):
                    score += 1
            scores[query_type] = score

        # Find best match
        max_score = max(scores.values()) if scores else 0

        if max_score > 0:
            best_type = max(scores, key=scores.get)
            # Confidence based on how many patterns matched vs total patterns
            confidence = min(scores[best_type] / len(self.PATTERNS[best_type]), 1.0)
            logger.debug(f"Query classified as {best_type.value} (confidence: {confidence:.2f})")
            return best_type, confidence

        return QueryType.GENERAL, 0.5

    def get_search_params(self, query_type: QueryType) -> Dict[str, Any]:
        """Get optimal search parameters for a query type"""
        return self.SEARCH_PARAMS.get(query_type, self.SEARCH_PARAMS[QueryType.GENERAL])

    def get_generation_params(self, query_type: QueryType) -> Dict[str, Any]:
        """Get optimal generation parameters for a query type"""
        return self.GENERATION_PARAMS.get(query_type, self.GENERATION_PARAMS[QueryType.GENERAL])


# Singleton instance
_classifier = None


def get_query_classifier() -> QueryClassifier:
    """Get singleton query classifier instance"""
    global _classifier
    if _classifier is None:
        _classifier = QueryClassifier()
    return _classifier


if __name__ == "__main__":
    # Test the classifier
    classifier = QueryClassifier()

    test_queries = [
        "What luxury hotels do you have in Mauritius?",
        "How much for a week in Kenya?",
        "How do I create a quote?",
        "Tell me about Zanzibar",
        "Compare luxury vs budget options in Mauritius",
        "What's the best time to visit Maldives?",
        "Show me beach resorts",
    ]

    print("Query Classification Test")
    print("=" * 60)

    for query in test_queries:
        query_type, confidence = classifier.classify(query)
        params = classifier.get_search_params(query_type)
        print(f"\nQuery: {query}")
        print(f"  Type: {query_type.value}")
        print(f"  Confidence: {confidence:.2f}")
        print(f"  Search k: {params['k']}, MMR: {params['use_mmr']}, Rerank: {params['use_rerank']}")
