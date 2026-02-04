"""
Query Classifier Unit Tests

Tests for the query classification service.
"""

import pytest


class TestQueryType:
    """Tests for QueryType enum."""

    def test_query_type_values(self):
        """QueryType should have expected values."""
        from src.services.query_classifier import QueryType

        assert QueryType.HOTEL_INFO.value == "hotel_info"
        assert QueryType.PRICING.value == "pricing"
        assert QueryType.PLATFORM_HELP.value == "platform_help"
        assert QueryType.DESTINATION_INFO.value == "destination"
        assert QueryType.COMPARISON.value == "comparison"
        assert QueryType.BOOKING_PROCESS.value == "booking"
        assert QueryType.GENERAL.value == "general"


class TestQueryClassifier:
    """Tests for QueryClassifier class."""

    @pytest.fixture
    def classifier(self):
        """Create a QueryClassifier instance."""
        from src.services.query_classifier import QueryClassifier
        return QueryClassifier()

    # Hotel Info Classification Tests
    def test_classifies_hotel_query(self, classifier):
        """Should classify hotel queries correctly."""
        from src.services.query_classifier import QueryType

        query_type, confidence = classifier.classify("What luxury hotels do you have?")
        assert query_type == QueryType.HOTEL_INFO

    def test_classifies_resort_query(self, classifier):
        """Should classify resort queries as hotel info."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("Show me beach resorts in Mauritius")
        assert query_type == QueryType.HOTEL_INFO

    def test_classifies_accommodation_query(self, classifier):
        """Should classify accommodation queries as hotel info."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("What accommodation options are there?")
        assert query_type == QueryType.HOTEL_INFO

    # Pricing Classification Tests
    def test_classifies_price_query(self, classifier):
        """Should classify price queries correctly."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("How much does it cost?")
        assert query_type == QueryType.PRICING

    def test_classifies_budget_query(self, classifier):
        """Should classify budget queries as pricing."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("What's my budget cost for a week?")
        assert query_type == QueryType.PRICING

    def test_classifies_rate_query(self, classifier):
        """Should classify rate queries as pricing."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("What are the rates per night?")
        assert query_type == QueryType.PRICING

    # Platform Help Classification Tests
    def test_classifies_platform_help_query(self, classifier):
        """Should classify platform help queries correctly."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("How do I create a quote?")
        assert query_type == QueryType.PLATFORM_HELP

    def test_classifies_dashboard_query(self, classifier):
        """Should classify dashboard queries as platform help."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("Where is the dashboard setting?")
        assert query_type == QueryType.PLATFORM_HELP

    # Destination Classification Tests
    def test_classifies_destination_query(self, classifier):
        """Should classify destination queries correctly."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("Tell me about Zanzibar")
        assert query_type == QueryType.DESTINATION_INFO

    def test_classifies_best_time_query(self, classifier):
        """Should classify best time queries as destination info."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("Best time to visit Maldives?")
        assert query_type == QueryType.DESTINATION_INFO

    # Comparison Classification Tests
    def test_classifies_comparison_query(self, classifier):
        """Should classify comparison queries correctly."""
        from src.services.query_classifier import QueryType

        # Use a clearer comparison query without triggering other patterns
        query_type, _ = classifier.classify("Which is better: option A or option B?")
        assert query_type == QueryType.COMPARISON

    def test_classifies_which_recommend_query(self, classifier):
        """Should classify 'which recommend' queries as comparison."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("Which destination would you recommend between these?")
        assert query_type == QueryType.COMPARISON

    # Booking Classification Tests
    def test_classifies_booking_query(self, classifier):
        """Should classify booking queries correctly."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("What is the booking process?")
        assert query_type == QueryType.BOOKING_PROCESS

    def test_classifies_reservation_query(self, classifier):
        """Should classify reservation queries as booking."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("What's the reservation confirmation procedure?")
        assert query_type == QueryType.BOOKING_PROCESS

    # General Classification Tests
    def test_classifies_general_query(self, classifier):
        """Should classify unmatched queries as general."""
        from src.services.query_classifier import QueryType

        query_type, confidence = classifier.classify("Hello, I have a random question")
        assert query_type == QueryType.GENERAL
        assert confidence == 0.5

    # Confidence Tests
    def test_returns_confidence_score(self, classifier):
        """Should return confidence score between 0 and 1."""
        _, confidence = classifier.classify("What luxury hotels in Mauritius?")

        assert 0 <= confidence <= 1

    def test_high_confidence_for_clear_queries(self, classifier):
        """Should return higher confidence for clear queries."""
        _, confidence = classifier.classify("What hotels do you have?")

        assert confidence > 0


class TestGetSearchParams:
    """Tests for search parameters retrieval."""

    @pytest.fixture
    def classifier(self):
        from src.services.query_classifier import QueryClassifier
        return QueryClassifier()

    def test_hotel_search_params(self, classifier):
        """Hotel queries should have diversity-focused params."""
        from src.services.query_classifier import QueryType

        params = classifier.get_search_params(QueryType.HOTEL_INFO)

        assert params["k"] == 6
        assert params["use_mmr"] is True
        assert params["use_rerank"] is True

    def test_pricing_search_params(self, classifier):
        """Pricing queries should have relevance-focused params."""
        from src.services.query_classifier import QueryType

        params = classifier.get_search_params(QueryType.PRICING)

        assert params["k"] == 4
        assert params["use_mmr"] is False

    def test_platform_help_search_params(self, classifier):
        """Platform help queries should have simple params."""
        from src.services.query_classifier import QueryType

        params = classifier.get_search_params(QueryType.PLATFORM_HELP)

        assert params["k"] == 3
        assert params["use_rerank"] is False

    def test_general_search_params(self, classifier):
        """General queries should have balanced params."""
        from src.services.query_classifier import QueryType

        params = classifier.get_search_params(QueryType.GENERAL)

        assert "k" in params
        assert "use_mmr" in params


class TestGetGenerationParams:
    """Tests for generation parameters retrieval."""

    @pytest.fixture
    def classifier(self):
        from src.services.query_classifier import QueryClassifier
        return QueryClassifier()

    def test_pricing_generation_params(self, classifier):
        """Pricing should have low temperature for accuracy."""
        from src.services.query_classifier import QueryType

        params = classifier.get_generation_params(QueryType.PRICING)

        assert params["temperature"] == 0.3
        assert "max_tokens" in params

    def test_destination_generation_params(self, classifier):
        """Destination should have higher temperature for creativity."""
        from src.services.query_classifier import QueryType

        params = classifier.get_generation_params(QueryType.DESTINATION_INFO)

        assert params["temperature"] == 0.7

    def test_comparison_generation_params(self, classifier):
        """Comparison should have higher max_tokens for detail."""
        from src.services.query_classifier import QueryType

        params = classifier.get_generation_params(QueryType.COMPARISON)

        assert params["max_tokens"] == 600


class TestSingletonPattern:
    """Tests for singleton pattern."""

    def test_get_query_classifier_returns_singleton(self):
        """get_query_classifier should return same instance."""
        from src.services.query_classifier import get_query_classifier

        classifier1 = get_query_classifier()
        classifier2 = get_query_classifier()

        assert classifier1 is classifier2

    def test_singleton_is_query_classifier(self):
        """Singleton should be a QueryClassifier instance."""
        from src.services.query_classifier import get_query_classifier, QueryClassifier

        classifier = get_query_classifier()

        assert isinstance(classifier, QueryClassifier)


class TestPatternMatching:
    """Tests for pattern matching behavior."""

    @pytest.fixture
    def classifier(self):
        from src.services.query_classifier import QueryClassifier
        return QueryClassifier()

    def test_case_insensitive_matching(self, classifier):
        """Patterns should match case-insensitively."""
        from src.services.query_classifier import QueryType

        query_type1, _ = classifier.classify("WHAT HOTELS DO YOU HAVE?")
        query_type2, _ = classifier.classify("what hotels do you have?")

        assert query_type1 == query_type2 == QueryType.HOTEL_INFO

    def test_multiple_pattern_matches_increase_confidence(self, classifier):
        """Multiple pattern matches should increase confidence."""
        from src.services.query_classifier import QueryType

        # Single pattern match
        _, conf1 = classifier.classify("hotel")

        # Multiple pattern matches
        _, conf2 = classifier.classify("What luxury hotels and resorts do you have?")

        # Both should be hotel_info, but second should have higher or equal confidence
        assert conf2 >= conf1


class TestEdgeCases:
    """Edge case tests for query classifier."""

    @pytest.fixture
    def classifier(self):
        from src.services.query_classifier import QueryClassifier
        return QueryClassifier()

    def test_empty_query(self, classifier):
        """Should handle empty query."""
        from src.services.query_classifier import QueryType

        query_type, confidence = classifier.classify("")

        assert query_type == QueryType.GENERAL
        assert confidence == 0.5

    def test_whitespace_only_query(self, classifier):
        """Should handle whitespace-only query."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("   ")

        assert query_type == QueryType.GENERAL

    def test_very_long_query(self, classifier):
        """Should handle very long queries."""
        from src.services.query_classifier import QueryType

        long_query = "What hotels " + "do you have? " * 100
        query_type, _ = classifier.classify(long_query)

        assert query_type == QueryType.HOTEL_INFO

    def test_special_characters_in_query(self, classifier):
        """Should handle special characters."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("What hotels??? !!! @#$%")

        assert query_type == QueryType.HOTEL_INFO

    def test_numeric_query(self, classifier):
        """Should handle numeric queries."""
        from src.services.query_classifier import QueryType

        query_type, _ = classifier.classify("12345")

        assert query_type == QueryType.GENERAL


class TestMixedQueryTypes:
    """Tests for queries with multiple type indicators."""

    @pytest.fixture
    def classifier(self):
        from src.services.query_classifier import QueryClassifier
        return QueryClassifier()

    def test_hotel_and_price(self, classifier):
        """Query mentioning hotels and price."""
        query_type, _ = classifier.classify("What's the price for luxury hotels?")

        # Should classify as one type (not crash)
        assert query_type is not None

    def test_destination_and_booking(self, classifier):
        """Query mentioning destination and booking."""
        query_type, _ = classifier.classify("How do I book a trip to Zanzibar?")

        assert query_type is not None


class TestSearchParamsEdgeCases:
    """Edge cases for search parameters."""

    @pytest.fixture
    def classifier(self):
        from src.services.query_classifier import QueryClassifier
        return QueryClassifier()

    def test_all_query_types_have_params(self, classifier):
        """All query types should have search params defined."""
        from src.services.query_classifier import QueryType

        for query_type in QueryType:
            params = classifier.get_search_params(query_type)
            assert "k" in params
            assert "use_mmr" in params

    def test_params_k_is_positive(self, classifier):
        """k parameter should be positive."""
        from src.services.query_classifier import QueryType

        for query_type in QueryType:
            params = classifier.get_search_params(query_type)
            assert params["k"] > 0


class TestGenerationParamsEdgeCases:
    """Edge cases for generation parameters."""

    @pytest.fixture
    def classifier(self):
        from src.services.query_classifier import QueryClassifier
        return QueryClassifier()

    def test_all_query_types_have_gen_params(self, classifier):
        """All query types should have generation params defined."""
        from src.services.query_classifier import QueryType

        for query_type in QueryType:
            params = classifier.get_generation_params(query_type)
            assert "temperature" in params
            assert "max_tokens" in params

    def test_temperature_in_valid_range(self, classifier):
        """Temperature should be between 0 and 1."""
        from src.services.query_classifier import QueryType

        for query_type in QueryType:
            params = classifier.get_generation_params(query_type)
            assert 0 <= params["temperature"] <= 1

    def test_max_tokens_is_positive(self, classifier):
        """max_tokens should be positive."""
        from src.services.query_classifier import QueryType

        for query_type in QueryType:
            params = classifier.get_generation_params(query_type)
            assert params["max_tokens"] > 0
