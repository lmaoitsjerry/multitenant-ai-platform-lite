"""
Travel Pages + Helpdesk RAG Integration Tests

Tests for the changes made in the travel/helpdesk integration update:
- Test 1: Transfer normalization handles both response shapes (frontend logic test)
- Test 2: TransfersList and ActivitiesList no longer import hotelbedsApi (guard rail)
- Test 3: Activities API call uses object params, not positional args (code pattern test)
- Test 4: Helpdesk passes citations to LLM for general queries (Step 5 fix)
- Test 5: Helpdesk forwards use_rerank from classifier
- Test 6: HelpDeskPanel METHOD_LABELS mapping is complete and correct
- Test 7: Helpdesk platform queries are unaffected (regression guard)
"""

import os
import re
import pytest
from unittest.mock import patch, MagicMock


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.tenant_id = "test_tenant"
    config.company_name = "Test Company"
    return config


FRONTEND_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend", "tenant-dashboard", "src"
)


# ==================== Test 1: Transfer normalization ====================

class TestTransferNormalization:
    """Test 1: normalizeTransfer handles both Cloud Run and BigQuery shapes."""

    def _normalize_transfer(self, raw, source):
        """
        Replicate the normalizeTransfer function from TransfersList.jsx.
        This must stay in sync with the frontend implementation.
        """
        if source == 'cloud_run':
            return {
                'transfer_id': raw.get('transfer_id'),
                'route': raw.get('route'),
                'vehicle_type': raw.get('vehicle_type'),
                'vehicle_category': raw.get('vehicle_category'),
                'price': raw.get('price_per_transfer'),
                'price_child': None,
                'currency': raw.get('currency', 'EUR'),
                'max_passengers': raw.get('max_passengers'),
                'duration_minutes': raw.get('duration_minutes'),
                'pricing_type': 'per_transfer',
                'source': 'cloud_run',
                'hotel_name': None,
            }
        # BigQuery format
        return {
            'transfer_id': f"bq_{raw.get('hotel_name')}",
            'route': f"Airport to {raw.get('hotel_name')}",
            'vehicle_type': 'Shared Transfer',
            'vehicle_category': 'Standard',
            'price': raw.get('transfers_adult'),
            'price_child': raw.get('transfers_child'),
            'currency': raw.get('currency', 'ZAR'),
            'max_passengers': None,
            'duration_minutes': None,
            'pricing_type': 'per_person',
            'source': 'bigquery',
            'hotel_name': raw.get('hotel_name'),
        }

    REQUIRED_FIELDS = [
        'transfer_id', 'route', 'vehicle_type', 'vehicle_category',
        'price', 'price_child', 'currency', 'max_passengers',
        'duration_minutes', 'pricing_type', 'source', 'hotel_name',
    ]

    def test_cloud_run_transfer_normalization(self):
        """Cloud Run transfer should normalize to standard shape."""
        cloud_run_transfer = {
            'transfer_id': 'cr_123',
            'route': 'Zanzibar Airport to Stone Town',
            'vehicle_type': 'Private Car',
            'vehicle_category': 'Luxury',
            'price_per_transfer': 85.0,
            'currency': 'EUR',
            'max_passengers': 4,
            'duration_minutes': 45,
        }

        result = self._normalize_transfer(cloud_run_transfer, 'cloud_run')

        # All required fields present
        for field in self.REQUIRED_FIELDS:
            assert field in result, f"Missing field: {field}"

        # Correct values
        assert result['transfer_id'] == 'cr_123'
        assert result['route'] == 'Zanzibar Airport to Stone Town'
        assert result['vehicle_type'] == 'Private Car'
        assert result['vehicle_category'] == 'Luxury'
        assert result['price'] == 85.0
        assert result['pricing_type'] == 'per_transfer'
        assert result['source'] == 'cloud_run'
        assert result['currency'] == 'EUR'
        assert result['max_passengers'] == 4
        assert result['duration_minutes'] == 45
        assert result['price_child'] is None
        assert result['hotel_name'] is None

    def test_bigquery_transfer_normalization(self):
        """BigQuery transfer should normalize to standard shape."""
        bq_transfer = {
            'hotel_name': 'Zanzibar Beach Resort',
            'transfers_adult': 35.0,
            'transfers_child': 20.0,
            'currency': 'ZAR',
        }

        result = self._normalize_transfer(bq_transfer, 'bigquery')

        # All required fields present
        for field in self.REQUIRED_FIELDS:
            assert field in result, f"Missing field: {field}"

        # Correct values
        assert result['transfer_id'] == 'bq_Zanzibar Beach Resort'
        assert result['route'] == 'Airport to Zanzibar Beach Resort'
        assert result['vehicle_type'] == 'Shared Transfer'
        assert result['vehicle_category'] == 'Standard'
        assert result['price'] == 35.0
        assert result['price_child'] == 20.0
        assert result['pricing_type'] == 'per_person'
        assert result['source'] == 'bigquery'
        assert result['currency'] == 'ZAR'
        assert result['max_passengers'] is None
        assert result['duration_minutes'] is None
        assert result['hotel_name'] == 'Zanzibar Beach Resort'

    def test_both_shapes_have_identical_keys(self):
        """Both normalized shapes should have the exact same set of keys."""
        cloud_run_raw = {
            'transfer_id': 'cr_1', 'route': 'A to B', 'vehicle_type': 'Car',
            'vehicle_category': 'Standard', 'price_per_transfer': 50,
            'currency': 'EUR', 'max_passengers': 3, 'duration_minutes': 30,
        }
        bq_raw = {
            'hotel_name': 'Hotel X', 'transfers_adult': 25,
            'transfers_child': 15, 'currency': 'ZAR',
        }

        cr_result = self._normalize_transfer(cloud_run_raw, 'cloud_run')
        bq_result = self._normalize_transfer(bq_raw, 'bigquery')

        assert set(cr_result.keys()) == set(bq_result.keys()), \
            f"Key mismatch: CR={set(cr_result.keys())}, BQ={set(bq_result.keys())}"

    def test_no_undefined_values_cloud_run(self):
        """Cloud Run normalized transfer should have no undefined/missing values for required fields."""
        cloud_run_raw = {
            'transfer_id': 'cr_1', 'route': 'A to B', 'vehicle_type': 'Car',
            'vehicle_category': 'Standard', 'price_per_transfer': 50,
            'currency': 'EUR', 'max_passengers': 3, 'duration_minutes': 30,
        }
        result = self._normalize_transfer(cloud_run_raw, 'cloud_run')

        # No key should be missing (all should be explicitly set)
        for key in self.REQUIRED_FIELDS:
            assert key in result, f"Key {key} missing from result"
            # Value can be None (explicitly set) but should not be a sentinel/undefined
            if result[key] is not None:
                assert result[key] != '', f"Key {key} has empty string value"

    def test_no_undefined_values_bigquery(self):
        """BigQuery normalized transfer should have no undefined/missing values."""
        bq_raw = {
            'hotel_name': 'Hotel X', 'transfers_adult': 25,
            'transfers_child': 15, 'currency': 'ZAR',
        }
        result = self._normalize_transfer(bq_raw, 'bigquery')

        for key in self.REQUIRED_FIELDS:
            assert key in result, f"Key {key} missing from result"

    def test_cloud_run_default_currency(self):
        """Cloud Run transfer without currency should default to EUR."""
        raw = {
            'transfer_id': 'cr_1', 'route': 'A to B', 'vehicle_type': 'Car',
            'vehicle_category': 'Standard', 'price_per_transfer': 50,
            'max_passengers': 3, 'duration_minutes': 30,
        }
        result = self._normalize_transfer(raw, 'cloud_run')
        assert result['currency'] == 'EUR'

    def test_bigquery_default_currency(self):
        """BigQuery transfer without currency should default to ZAR."""
        raw = {'hotel_name': 'Hotel X', 'transfers_adult': 25, 'transfers_child': 15}
        result = self._normalize_transfer(raw, 'bigquery')
        assert result['currency'] == 'ZAR'


# ==================== Test 2: No hotelbedsApi imports ====================

class TestNoHotelbedsApiImports:
    """Test 2: TransfersList and ActivitiesList no longer import hotelbedsApi."""

    def test_transfers_list_no_hotelbeds_import(self):
        """TransfersList.jsx should not contain hotelbedsApi references."""
        filepath = os.path.join(FRONTEND_BASE, "pages", "travel", "TransfersList.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'hotelbedsApi' not in content, \
            "TransfersList.jsx still contains 'hotelbedsApi' reference"
        assert not re.search(r'import.*hotelbeds', content, re.IGNORECASE), \
            "TransfersList.jsx still has a hotelbeds import"

    def test_activities_list_no_hotelbeds_import(self):
        """ActivitiesList.jsx should not contain hotelbedsApi references."""
        filepath = os.path.join(FRONTEND_BASE, "pages", "travel", "ActivitiesList.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'hotelbedsApi' not in content, \
            "ActivitiesList.jsx still contains 'hotelbedsApi' reference"
        assert not re.search(r'import.*hotelbeds', content, re.IGNORECASE), \
            "ActivitiesList.jsx still has a hotelbeds import"

    def test_transfers_list_uses_transfers_api(self):
        """TransfersList.jsx should import and use transfersApi."""
        filepath = os.path.join(FRONTEND_BASE, "pages", "travel", "TransfersList.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'transfersApi' in content, \
            "TransfersList.jsx should import transfersApi"
        assert 'transfersApi.search' in content, \
            "TransfersList.jsx should call transfersApi.search"

    def test_activities_list_uses_activities_api(self):
        """ActivitiesList.jsx should import and use activitiesApi."""
        filepath = os.path.join(FRONTEND_BASE, "pages", "travel", "ActivitiesList.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'activitiesApi' in content, \
            "ActivitiesList.jsx should import activitiesApi"
        assert 'activitiesApi.search' in content, \
            "ActivitiesList.jsx should call activitiesApi.search"

    def test_transfers_list_uses_destination_iata(self):
        """TransfersList.jsx should import getDestinationIata."""
        filepath = os.path.join(FRONTEND_BASE, "pages", "travel", "TransfersList.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'getDestinationIata' in content, \
            "TransfersList.jsx should import getDestinationIata"


# ==================== Test 3: Activities API uses object params ====================

class TestActivitiesApiObjectParams:
    """Test 3: Activities API call uses object params, not positional args."""

    def test_activities_search_called_with_object_params(self):
        """activitiesApi.search should be called with a single object argument."""
        filepath = os.path.join(FRONTEND_BASE, "pages", "travel", "ActivitiesList.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the activitiesApi.search call
        search_calls = re.findall(r'activitiesApi\.search\(([\s\S]*?)\)', content)
        assert len(search_calls) > 0, "No activitiesApi.search() call found"

        for call_args in search_calls:
            # Should start with { (object literal), not a variable name (positional)
            stripped = call_args.strip()
            assert stripped.startswith('{'), \
                f"activitiesApi.search called with positional args: '{stripped[:80]}...'"

    def test_activities_search_includes_required_keys(self):
        """activitiesApi.search object should include destination and participants."""
        filepath = os.path.join(FRONTEND_BASE, "pages", "travel", "ActivitiesList.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract the object passed to activitiesApi.search
        search_match = re.search(r'activitiesApi\.search\(\{([\s\S]*?)\}\)', content)
        assert search_match, "activitiesApi.search({...}) pattern not found"

        obj_content = search_match.group(1)
        assert 'destination' in obj_content, "Missing 'destination' key in search params"
        assert 'participants' in obj_content, "Missing 'participants' key in search params"

    def test_activities_no_positional_search_pattern(self):
        """Should NOT have old-style positional call like search(destination, category, query)."""
        filepath = os.path.join(FRONTEND_BASE, "pages", "travel", "ActivitiesList.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Old pattern: activitiesApi.search(selectedDestination, selectedCategory, searchQuery)
        old_pattern = re.search(
            r'activitiesApi\.search\(\s*selected\w+\s*,',
            content
        )
        assert old_pattern is None, \
            "Found old positional-args pattern in activitiesApi.search call"

    def test_transfers_search_called_with_object_params(self):
        """transfersApi.search should also use object params."""
        filepath = os.path.join(FRONTEND_BASE, "pages", "travel", "TransfersList.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        search_calls = re.findall(r'transfersApi\.search\(([\s\S]*?)\)', content)
        assert len(search_calls) > 0, "No transfersApi.search() call found"

        for call_args in search_calls:
            stripped = call_args.strip()
            assert stripped.startswith('{'), \
                f"transfersApi.search called with positional args: '{stripped[:80]}...'"


# ==================== Test 4: Helpdesk passes citations to LLM ====================

class TestHelpdeskPassesCitationsToLLM:
    """Test 4: Helpdesk passes citations to LLM for general queries (Step 5 fix)."""

    def test_citations_passed_to_llm_for_general_travel_query(self, mock_config):
        """When no static match, LLM should receive dual KB citations, not empty list."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion
        from src.services.query_classifier import QueryType

        request = AskQuestion(question="What's the best time to visit Zanzibar?")

        # Mock classifier to return GENERAL (won't match static)
        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.GENERAL, 0.5)
            mock_instance.get_search_params.return_value = {
                "k": 5, "use_rerank": True
            }
            mock_classifier.return_value = mock_instance

            # Mock dual KB to return citations but no synthesized answer
            known_citations = [
                {
                    "content": "Best time to visit Zanzibar is June-October for dry season",
                    "score": 0.82,
                    "source": "travel_guide",
                    "source_type": "global_kb",
                    "visibility": "public"
                },
                {
                    "content": "Zanzibar has two rainy seasons: March-May and November-December",
                    "score": 0.75,
                    "source": "destination_info",
                    "source_type": "global_kb",
                    "visibility": "public"
                }
            ]

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                mock_search.return_value = {
                    "success": False,  # No global answer synthesized
                    "answer": "",
                    "citations": known_citations,
                    "confidence": 0,
                    "latency_ms": 100,
                    "sources_breakdown": {"global": 2, "private": 0, "total": 2}
                }

                with patch('src.api.helpdesk_routes.get_rag_service') as mock_rag:
                    mock_service = MagicMock()
                    mock_service.generate_response.return_value = {
                        "answer": "The best time to visit Zanzibar is June-October.",
                        "sources": []
                    }
                    mock_rag.return_value = mock_service

                    # Also mock get_smart_response to return general (no static match)
                    with patch('src.api.helpdesk_routes.get_smart_response') as mock_static:
                        mock_static.return_value = (
                            "I can help with various topics.",
                            "general",
                            []
                        )

                        result = ask_helpdesk(request, user=None, config=mock_config)

                    # THE KEY ASSERTION: LLM was called with our citations, NOT []
                    mock_service.generate_response.assert_called_once()
                    call_kwargs = mock_service.generate_response.call_args
                    actual_search_results = call_kwargs.kwargs.get(
                        'search_results',
                        call_kwargs[1].get('search_results') if len(call_kwargs) > 1 else None
                    )

                    # Handle both positional and keyword arg styles
                    if actual_search_results is None and call_kwargs.args:
                        # Might be positional
                        pass
                    if actual_search_results is None:
                        # Try getting from kwargs
                        actual_search_results = call_kwargs.kwargs.get('search_results', [])

                    assert len(actual_search_results) == 2, \
                        f"Expected 2 citations passed to LLM, got {len(actual_search_results)}"
                    assert actual_search_results[0]["content"] == known_citations[0]["content"]
                    assert actual_search_results[1]["content"] == known_citations[1]["content"]

        assert result["success"] is True
        assert result["method"] == "llm_synthesis"

    def test_empty_citations_still_works(self, mock_config):
        """When dual KB returns no citations, LLM should still work (empty list)."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion
        from src.services.query_classifier import QueryType

        request = AskQuestion(question="What's the best time to visit Zanzibar?")

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.GENERAL, 0.5)
            mock_instance.get_search_params.return_value = {"k": 5, "use_rerank": True}
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                mock_search.return_value = {
                    "success": False,
                    "answer": "",
                    "citations": [],  # Empty — no KB results at all
                    "confidence": 0,
                    "latency_ms": 50,
                    "sources_breakdown": {"global": 0, "private": 0, "total": 0}
                }

                with patch('src.api.helpdesk_routes.get_rag_service') as mock_rag:
                    mock_service = MagicMock()
                    mock_service.generate_response.return_value = {
                        "answer": "I'll try my best to help.",
                        "sources": []
                    }
                    mock_rag.return_value = mock_service

                    with patch('src.api.helpdesk_routes.get_smart_response') as mock_static:
                        mock_static.return_value = ("Default help.", "general", [])

                        result = ask_helpdesk(request, user=None, config=mock_config)

                    # Should work fine with empty citations
                    mock_service.generate_response.assert_called_once()
                    call_kwargs = mock_service.generate_response.call_args
                    actual_search_results = call_kwargs.kwargs.get('search_results', [])
                    assert actual_search_results == [], \
                        "With no citations, LLM should receive empty list"

        assert result["success"] is True


# ==================== Test 5: Helpdesk forwards use_rerank ====================

class TestHelpdeskForwardsUseRerank:
    """Test 5: Helpdesk forwards use_rerank from classifier to search."""

    def test_platform_help_forwards_use_rerank_false(self, mock_config):
        """PLATFORM_HELP queries should forward use_rerank=False."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion
        from src.services.query_classifier import QueryType

        request = AskQuestion(question="How do I use the dashboard settings?")

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.PLATFORM_HELP, 0.85)
            mock_instance.get_search_params.return_value = {
                "k": 3, "use_rerank": False  # PLATFORM_HELP has rerank=False
            }
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                mock_search.return_value = {
                    "success": True,
                    "answer": "Dashboard settings explanation",
                    "citations": [{"source": "KB", "score": 0.9, "source_type": "global_kb"}],
                    "confidence": 0.85,
                    "latency_ms": 80,
                    "sources_breakdown": {"global": 1, "private": 0, "total": 1}
                }

                ask_helpdesk(request, user=None, config=mock_config)

                # Assert use_rerank=False was forwarded
                mock_search.assert_called_once()
                call_kwargs = mock_search.call_args
                assert call_kwargs.kwargs.get('use_rerank') is False, \
                    f"Expected use_rerank=False for PLATFORM_HELP, got {call_kwargs.kwargs.get('use_rerank')}"

    def test_travel_query_forwards_use_rerank_true(self, mock_config):
        """Travel queries should forward use_rerank=True."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion
        from src.services.query_classifier import QueryType

        request = AskQuestion(question="What hotels are available in Zanzibar?")

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.HOTEL_INFO, 0.9)
            mock_instance.get_search_params.return_value = {
                "k": 6, "use_rerank": True  # HOTEL_INFO has rerank=True
            }
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                mock_search.return_value = {
                    "success": True,
                    "answer": "Zanzibar has many hotels",
                    "citations": [{"source": "KB", "score": 0.9, "source_type": "global_kb"}],
                    "confidence": 0.9,
                    "latency_ms": 120,
                    "sources_breakdown": {"global": 1, "private": 0, "total": 1}
                }

                ask_helpdesk(request, user=None, config=mock_config)

                # Assert use_rerank=True was forwarded
                mock_search.assert_called_once()
                call_kwargs = mock_search.call_args
                assert call_kwargs.kwargs.get('use_rerank') is True, \
                    f"Expected use_rerank=True for HOTEL_INFO, got {call_kwargs.kwargs.get('use_rerank')}"

    def test_booking_process_forwards_use_rerank_false(self, mock_config):
        """BOOKING_PROCESS queries should also forward use_rerank=False."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion
        from src.services.query_classifier import QueryType

        request = AskQuestion(question="How do I make a booking?")

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.BOOKING_PROCESS, 0.88)
            mock_instance.get_search_params.return_value = {
                "k": 3, "use_rerank": False  # BOOKING_PROCESS has rerank=False
            }
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                mock_search.return_value = {
                    "success": True,
                    "answer": "To make a booking...",
                    "citations": [{"source": "KB", "score": 0.88, "source_type": "global_kb"}],
                    "confidence": 0.88,
                    "latency_ms": 70,
                    "sources_breakdown": {"global": 1, "private": 0, "total": 1}
                }

                ask_helpdesk(request, user=None, config=mock_config)

                call_kwargs = mock_search.call_args
                assert call_kwargs.kwargs.get('use_rerank') is False, \
                    f"Expected use_rerank=False for BOOKING_PROCESS, got {call_kwargs.kwargs.get('use_rerank')}"

    def test_use_rerank_flows_through_to_rag_client(self, mock_config):
        """use_rerank should flow from search_dual_knowledge_base to search_travel_platform_rag."""
        from src.api.helpdesk_routes import search_dual_knowledge_base

        with patch('src.api.helpdesk_routes.search_travel_platform_rag') as mock_rag:
            mock_rag.return_value = {
                "success": True, "answer": "", "citations": [], "confidence": 0, "latency_ms": 0
            }
            with patch('src.api.helpdesk_routes.search_private_knowledge_base') as mock_private:
                mock_private.return_value = []

                # Call with use_rerank=False
                search_dual_knowledge_base(mock_config, "test", top_k=5, use_rerank=False)
                call_kwargs = mock_rag.call_args
                assert call_kwargs.kwargs.get('use_rerank') is False

                mock_rag.reset_mock()

                # Call with use_rerank=True
                search_dual_knowledge_base(mock_config, "test", top_k=5, use_rerank=True)
                call_kwargs = mock_rag.call_args
                assert call_kwargs.kwargs.get('use_rerank') is True


# ==================== Test 6: HelpDeskPanel METHOD_LABELS ====================

class TestHelpDeskPanelMethodLabels:
    """Test 6: HelpDeskPanel METHOD_LABELS are correctly defined."""

    def _get_method_labels_from_source(self):
        """Parse METHOD_LABELS from HelpDeskPanel.jsx source."""
        filepath = os.path.join(FRONTEND_BASE, "components", "layout", "HelpDeskPanel.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Extract METHOD_LABELS object
        match = re.search(r'const METHOD_LABELS\s*=\s*\{([\s\S]*?)\};', content)
        assert match, "METHOD_LABELS not found in HelpDeskPanel.jsx"
        return content, match.group(1)

    def test_method_labels_exists(self):
        """METHOD_LABELS constant should be defined."""
        content, _ = self._get_method_labels_from_source()
        assert 'METHOD_LABELS' in content

    def test_method_labels_has_dual_kb(self):
        """METHOD_LABELS should map dual_kb to 'Knowledge Base'."""
        _, labels_content = self._get_method_labels_from_source()
        assert 'dual_kb' in labels_content
        assert "'Knowledge Base'" in labels_content or '"Knowledge Base"' in labels_content

    def test_method_labels_has_private_kb_synthesis(self):
        """METHOD_LABELS should map private_kb_synthesis to 'Your Documents'."""
        _, labels_content = self._get_method_labels_from_source()
        assert 'private_kb_synthesis' in labels_content
        assert "'Your Documents'" in labels_content or '"Your Documents"' in labels_content

    def test_method_labels_has_smart_static(self):
        """METHOD_LABELS should map smart_static to 'Help Guide'."""
        _, labels_content = self._get_method_labels_from_source()
        assert 'smart_static' in labels_content
        assert "'Help Guide'" in labels_content or '"Help Guide"' in labels_content

    def test_method_labels_has_llm_synthesis(self):
        """METHOD_LABELS should map llm_synthesis to 'AI Generated'."""
        _, labels_content = self._get_method_labels_from_source()
        assert 'llm_synthesis' in labels_content
        assert "'AI Generated'" in labels_content or '"AI Generated"' in labels_content

    def test_method_labels_has_static_fallback(self):
        """METHOD_LABELS should map static_fallback to 'Help Guide'."""
        _, labels_content = self._get_method_labels_from_source()
        assert 'static_fallback' in labels_content

    def test_method_labels_covers_all_backend_methods(self):
        """METHOD_LABELS should cover all method values returned by the backend."""
        _, labels_content = self._get_method_labels_from_source()

        backend_methods = [
            'dual_kb', 'private_kb_synthesis', 'smart_static',
            'llm_synthesis', 'static_fallback'
        ]

        for method in backend_methods:
            assert method in labels_content, \
                f"Backend method '{method}' not found in METHOD_LABELS"

    def test_method_badge_renders_conditionally(self):
        """Method badge should only render when message.method is truthy."""
        filepath = os.path.join(FRONTEND_BASE, "components", "layout", "HelpDeskPanel.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for conditional rendering: {!isUser && message.method && (
        assert re.search(r'!isUser\s*&&\s*message\.method\s*&&', content), \
            "Method badge should have conditional rendering: !isUser && message.method &&"

    def test_method_badge_uses_fallback_for_unknown(self):
        """Unknown method should render empty string via || ''."""
        filepath = os.path.join(FRONTEND_BASE, "components", "layout", "HelpDeskPanel.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for fallback: METHOD_LABELS[message.method] || ''
        assert "|| ''" in content or '|| ""' in content, \
            "METHOD_LABELS lookup should have empty string fallback for unknown methods"

    def test_method_passed_from_api_response(self):
        """Assistant message should include method from API response."""
        filepath = os.path.join(FRONTEND_BASE, "components", "layout", "HelpDeskPanel.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        assert 'method: response.data.method' in content, \
            "Assistant message should include method: response.data.method"

    def test_sources_show_three(self):
        """Sources should show at least 3 items (not 2)."""
        filepath = os.path.join(FRONTEND_BASE, "components", "layout", "HelpDeskPanel.jsx")
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Should show 3+ sources (currently .slice(0, 4))
        import re
        match = re.search(r'\.slice\(0,\s*(\d+)\)', content)
        assert match, "sources.slice() not found"
        limit = int(match.group(1))
        assert limit >= 3, f"Sources display limit is {limit}, should be >= 3"
        assert '.slice(0, 2)' not in content, \
            "Old .slice(0, 2) pattern should be removed"


# ==================== Test 7: Platform queries unaffected ====================

class TestPlatformQueriesUnaffected:
    """Test 7: Platform queries still get smart_static responses."""

    def test_create_quote_gets_smart_static(self, mock_config):
        """'How do I create a quote?' should still return smart_static method."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion
        from src.services.query_classifier import QueryType

        request = AskQuestion(question="How do I create a quote?")

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.PLATFORM_HELP, 0.92)
            mock_instance.get_search_params.return_value = {
                "k": 3, "use_rerank": False
            }
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                # Simulate: no global answer but some low-relevance results
                mock_search.return_value = {
                    "success": False,
                    "answer": "",
                    "citations": [],
                    "confidence": 0,
                    "latency_ms": 50,
                    "sources_breakdown": {"global": 0, "private": 0, "total": 0}
                }

                result = ask_helpdesk(request, user=None, config=mock_config)

        assert result["success"] is True
        assert result["method"] == "smart_static", \
            f"Expected 'smart_static' method for quote query, got '{result.get('method')}'"
        assert "quote" in result["answer"].lower(), \
            "Smart static response for quote query should mention 'quote'"

    def test_create_invoice_gets_smart_static(self, mock_config):
        """'How do I generate an invoice?' should still return smart_static method."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion
        from src.services.query_classifier import QueryType

        request = AskQuestion(question="How do I generate an invoice?")

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.PLATFORM_HELP, 0.90)
            mock_instance.get_search_params.return_value = {
                "k": 3, "use_rerank": False
            }
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                mock_search.return_value = {
                    "success": False,
                    "answer": "",
                    "citations": [],
                    "confidence": 0,
                    "latency_ms": 50,
                    "sources_breakdown": {"global": 0, "private": 0, "total": 0}
                }

                result = ask_helpdesk(request, user=None, config=mock_config)

        assert result["success"] is True
        assert result["method"] == "smart_static", \
            f"Expected 'smart_static' method for invoice query, got '{result.get('method')}'"

    def test_pipeline_gets_smart_static(self, mock_config):
        """'What are the different pipeline stages?' should get smart_static."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion
        from src.services.query_classifier import QueryType

        request = AskQuestion(question="What are the different pipeline stages?")

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.PLATFORM_HELP, 0.85)
            mock_instance.get_search_params.return_value = {
                "k": 3, "use_rerank": False
            }
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                mock_search.return_value = {
                    "success": False,
                    "answer": "",
                    "citations": [],
                    "confidence": 0,
                    "latency_ms": 50,
                    "sources_breakdown": {"global": 0, "private": 0, "total": 0}
                }

                result = ask_helpdesk(request, user=None, config=mock_config)

        assert result["success"] is True
        assert result["method"] == "smart_static", \
            f"Expected 'smart_static' for pipeline query, got '{result.get('method')}'"
        assert "pipeline" in result["answer"].lower()

    def test_dual_kb_path_unchanged_for_successful_rag(self, mock_config):
        """When global RAG returns a good answer, dual_kb method should still work."""
        from src.api.helpdesk_routes import ask_helpdesk, AskQuestion
        from src.services.query_classifier import QueryType

        request = AskQuestion(question="What hotels are in Zanzibar?")

        with patch('src.api.helpdesk_routes.get_query_classifier') as mock_classifier:
            mock_instance = MagicMock()
            mock_instance.classify.return_value = (QueryType.HOTEL_INFO, 0.9)
            mock_instance.get_search_params.return_value = {
                "k": 6, "use_rerank": True
            }
            mock_classifier.return_value = mock_instance

            with patch('src.api.helpdesk_routes.search_dual_knowledge_base') as mock_search:
                mock_search.return_value = {
                    "success": True,
                    "answer": "Zanzibar has great hotels including...",
                    "citations": [
                        {"source": "KB", "score": 0.92, "source_type": "global_kb"}
                    ],
                    "confidence": 0.9,
                    "latency_ms": 150,
                    "sources_breakdown": {"global": 1, "private": 0, "total": 1}
                }

                result = ask_helpdesk(request, user=None, config=mock_config)

        assert result["success"] is True
        assert result["method"] == "dual_kb"
        assert "timing" in result
