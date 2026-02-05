"""
BigQuery Tool Unit Tests

Comprehensive tests for BigQueryTool:
- Initialization
- Hotel search queries
- Rate lookups
- Price calculation
- Consultant assignment
- Flight price lookup

Uses pytest with mocked BigQuery client.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import date


# ==================== Fixtures ====================

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig."""
    config = MagicMock()
    config.client_id = "test_tenant"
    config.gcp_project_id = "test-project"
    config.get_destination_search_terms.return_value = ["mauritius", "mu"]
    return config


@pytest.fixture
def mock_bigquery_client():
    """Create a mock BigQuery client."""
    client = MagicMock()
    return client


@pytest.fixture
def sample_hotel_results():
    """Create sample hotel rate results."""
    return [
        MagicMock(
            rate_id="RATE001",
            hotel_name="Solana Beach Resort",
            hotel_rating=5,
            room_type="Sea View",
            meal_plan="All Inclusive",
            total_7nights_pps=45000,
            total_7nights_single=52000,
            total_7nights_child=22000,
            check_in_date=date(2024, 6, 1),
            check_out_date=date(2024, 6, 8),
            nights=7
        ),
        MagicMock(
            rate_id="RATE002",
            hotel_name="Beach Resort",
            hotel_rating=4,
            room_type="Standard",
            meal_plan="Half Board",
            total_7nights_pps=35000,
            total_7nights_single=42000,
            total_7nights_child=18000,
            check_in_date=date(2024, 6, 1),
            check_out_date=date(2024, 6, 8),
            nights=7
        )
    ]


# ==================== Initialization Tests ====================

class TestBigQueryToolInit:
    """Test BigQueryTool initialization."""

    def test_init_with_config(self, mock_config):
        """Should initialize with config."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            assert tool.config == mock_config
            assert tool.project_id == "test-project"

    def test_init_creates_client(self, mock_config):
        """Should create BigQuery client."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            mock_bq.Client.assert_called_once_with(project="test-project")
            assert tool.client is not None

    def test_init_handles_client_error(self, mock_config):
        """Should handle client creation error gracefully."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.side_effect = Exception("Auth error")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            assert tool.client is None

    def test_init_creates_database_tables(self, mock_config):
        """Should create DatabaseTables instance."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            assert tool.db is not None


# ==================== Find Matching Hotels Tests ====================

class TestFindMatchingHotels:
    """Test find_matching_hotels method."""

    def test_find_matching_hotels_no_client(self, mock_config):
        """Should return empty list when no client."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.side_effect = Exception("No client")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            assert result == []

    def test_find_matching_hotels_basic_search(self, mock_config, mock_bigquery_client, sample_hotel_results):
        """Should execute basic hotel search."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = sample_hotel_results
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            assert len(result) == 2
            mock_bigquery_client.query.assert_called_once()

    def test_find_matching_hotels_uses_destination_search_terms(self, mock_config, mock_bigquery_client):
        """Should use destination search terms from config."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            mock_config.get_destination_search_terms.assert_called_with("Mauritius")

    def test_find_matching_hotels_with_meal_plan_filter(self, mock_config, mock_bigquery_client):
        """Should filter by meal plan when specified."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2,
                meal_plan_pref="All Inclusive"
            )

            # Verify query includes meal plan filter
            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "meal_plan" in call_args

    def test_find_matching_hotels_handles_query_error(self, mock_config, mock_bigquery_client):
        """Should return empty list on query error."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_bigquery_client.query.side_effect = Exception("Query error")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            assert result == []


# ==================== Find Rates By Hotel Names Tests ====================

class TestFindRatesByHotelNames:
    """Test find_rates_by_hotel_names method."""

    def test_find_rates_no_client(self, mock_config):
        """Should return empty list when no client."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.side_effect = Exception("No client")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.find_rates_by_hotel_names(
                hotel_names=["Hotel A"],
                nights=7,
                check_in="2024-06-01",
                check_out="2024-06-08"
            )

            assert result == []

    def test_find_rates_empty_hotel_names(self, mock_config, mock_bigquery_client):
        """Should return empty list for empty hotel names."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.find_rates_by_hotel_names(
                hotel_names=[],
                nights=7,
                check_in="2024-06-01",
                check_out="2024-06-08"
            )

            assert result == []

    def test_find_rates_by_names_uses_like_patterns(self, mock_config, mock_bigquery_client):
        """Should use LIKE patterns for flexible matching."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_rates_by_hotel_names(
                hotel_names=["Diamonds Leisure Beach Resort"],
                nights=7,
                check_in="2024-06-01",
                check_out="2024-06-08"
            )

            # Query should include LIKE clause
            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "LIKE" in call_args


# ==================== Search Hotels By Name Tests ====================

class TestSearchHotelsByName:
    """Test search_hotels_by_name method."""

    def test_search_hotels_no_client(self, mock_config):
        """Should return empty list when no client."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.side_effect = Exception("No client")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.search_hotels_by_name("Solana")

            assert result == []

    def test_search_hotels_by_name_basic(self, mock_config, mock_bigquery_client):
        """Should search hotels by name."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_results = [
                MagicMock(hotel_name="Solana Beach", hotel_rating=5, destination="Mauritius")
            ]
            query_job = MagicMock()
            query_job.result.return_value = mock_results
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.search_hotels_by_name("Solana")

            assert len(result) == 1
            mock_bigquery_client.query.assert_called_once()

    def test_search_hotels_respects_limit(self, mock_config, mock_bigquery_client):
        """Should respect limit parameter."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.search_hotels_by_name("Hotel", limit=10)

            # Query should include limit
            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "LIMIT" in call_args


# ==================== Get Hotel Info Tests ====================

class TestGetHotelInfo:
    """Test get_hotel_info method."""

    def test_get_hotel_info_no_client(self, mock_config):
        """Should return None when no client."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.side_effect = Exception("No client")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_hotel_info("Solana Beach")

            assert result is None

    def test_get_hotel_info_found(self, mock_config, mock_bigquery_client):
        """Should return hotel info when found."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_result = MagicMock(
                hotel_name="Solana Beach",
                hotel_rating=5,
                min_price_pps=40000,
                max_price_pps=60000
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_result])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_hotel_info("Solana Beach")

            assert result is not None

    def test_get_hotel_info_not_found(self, mock_config, mock_bigquery_client):
        """Should return None when hotel not found."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = iter([])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_hotel_info("Nonexistent Hotel")

            assert result is None


# ==================== Calculate Quote Price Tests ====================

class TestCalculateQuotePrice:
    """Test calculate_quote_price method."""

    def test_calculate_quote_no_client(self, mock_config):
        """Should return None when no client."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.side_effect = Exception("No client")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=2
            )

            assert result is None

    def test_calculate_quote_basic(self, mock_config, mock_bigquery_client):
        """Should calculate basic quote price."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=45000,
                total_7nights_single=52000,
                total_7nights_child=22000
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=2
            )

            assert result is not None
            assert 'per_person_rates' in result
            assert 'traveler_counts' in result
            assert 'totals' in result

    def test_calculate_quote_single_traveler(self, mock_config, mock_bigquery_client):
        """Should use single rate for solo traveler."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=45000,
                total_7nights_single=52000,
                total_7nights_child=22000
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=1
            )

            assert result is not None
            assert result['traveler_counts']['adults_single'] == 1
            assert result['traveler_counts']['adults_sharing'] == 0

    def test_calculate_quote_with_children(self, mock_config, mock_bigquery_client):
        """Should calculate price with children."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=45000,
                total_7nights_single=52000,
                total_7nights_child=22000
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=2,
                children_ages=[5, 8]
            )

            assert result is not None
            assert result['traveler_counts']['children'] == 2
            assert result['totals']['children'] > 0

    def test_calculate_quote_with_infants(self, mock_config, mock_bigquery_client):
        """Should handle infants with flat rate."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=45000,
                total_7nights_single=52000,
                total_7nights_child=22000
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=2,
                children_ages=[1]  # Infant (<2)
            )

            assert result is not None
            assert result['traveler_counts']['infants'] == 1
            assert result['per_person_rates']['infant'] == 1000  # Flat rate

    def test_calculate_quote_mixed_rooms(self, mock_config, mock_bigquery_client):
        """Should handle mixed room configuration."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=45000,
                total_7nights_single=52000,
                total_7nights_child=22000
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=3,
                single_adults=1  # 1 single, 2 sharing
            )

            assert result is not None
            assert result['traveler_counts']['adults_sharing'] == 2
            assert result['traveler_counts']['adults_single'] == 1

    def test_calculate_quote_rate_not_found(self, mock_config, mock_bigquery_client):
        """Should return None when rate not found."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = iter([])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="NONEXISTENT",
                adults=2
            )

            assert result is None


# ==================== Consultant Round Robin Tests ====================

class TestConsultantRoundRobin:
    """Test get_next_consultant_round_robin method."""

    def test_consultant_no_client(self, mock_config):
        """Should return None when no client."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.side_effect = Exception("No client")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_next_consultant_round_robin()

            assert result is None

    def test_consultant_found(self, mock_config, mock_bigquery_client):
        """Should return consultant when found."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client

            mock_consultant = MagicMock(
                consultant_id="C001",
                name="John Doe",
                email="john@example.com"
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_consultant])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_next_consultant_round_robin()

            assert result is not None

    def test_consultant_not_found(self, mock_config, mock_bigquery_client):
        """Should return None when no consultants."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client

            query_job = MagicMock()
            query_job.result.return_value = iter([])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_next_consultant_round_robin()

            assert result is None

    def test_consultant_handles_missing_table(self, mock_config, mock_bigquery_client):
        """Should handle missing consultants table gracefully."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client

            mock_bigquery_client.query.side_effect = Exception("Table not found")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_next_consultant_round_robin()

            assert result is None


# ==================== Flight Price Tests ====================

class TestFlightPrice:
    """Test get_flight_price method."""

    def test_flight_price_no_client(self, mock_config):
        """Should return 0 when no client."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.side_effect = Exception("No client")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_flight_price("Mauritius", "2024-06-01")

            assert result == 0

    def test_flight_price_found(self, mock_config, mock_bigquery_client):
        """Should return flight price when found."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_flight = MagicMock(price_per_person=15000)
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_flight])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_flight_price("Mauritius", "2024-06-01")

            assert result == 15000

    def test_flight_price_not_found(self, mock_config, mock_bigquery_client):
        """Should return 0 when flight not found."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = iter([])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_flight_price("Unknown", "2024-06-01")

            assert result == 0

    def test_flight_price_handles_missing_table(self, mock_config, mock_bigquery_client):
        """Should return 0 when flight table missing."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_bigquery_client.query.side_effect = Exception("Table not found")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_flight_price("Mauritius", "2024-06-01")

            assert result == 0


# ==================== Hotel Name Normalization Tests ====================

class TestHotelNameNormalization:
    """Test hotel name normalization methods."""

    def test_normalize_hotel_name_removes_stars(self, mock_config):
        """Should remove star symbols from hotel name."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            normalized = tool._normalize_hotel_name("5* Grand Hotel")
            assert "5*" not in normalized

    def test_normalize_hotel_name_lowercase(self, mock_config):
        """Should convert to lowercase."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            normalized = tool._normalize_hotel_name("Grand HOTEL")
            assert normalized == normalized.lower()

    def test_extract_hotel_keywords_filters_common(self, mock_config):
        """Should filter common words from hotel name."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            keywords = tool._extract_hotel_keywords("The Grand Hotel Resort & Spa")

            # Should not include common words
            assert "the" not in keywords
            assert "hotel" not in keywords
            assert "resort" not in keywords
            assert "spa" not in keywords
            # Should include distinctive word
            assert "grand" in keywords

    def test_extract_hotel_keywords_empty_name(self, mock_config):
        """Should handle empty hotel name."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            keywords = tool._extract_hotel_keywords("")
            assert keywords == []


# ==================== Query Timeout Tests ====================

class TestQueryTimeout:
    """Test query timeout handling."""

    def test_find_matching_hotels_has_timeout(self, mock_config, mock_bigquery_client):
        """Query should have timeout set."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            # Verify timeout was passed to result()
            query_job.result.assert_called_with(timeout=8.0)


# ==================== Edge Cases Tests ====================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_find_matching_hotels_with_empty_destination(self, mock_config, mock_bigquery_client):
        """Should handle empty destination search terms."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            # Return empty search terms
            mock_config.get_destination_search_terms.return_value = []

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            # Should not crash
            result = tool.find_matching_hotels(
                destination="",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            assert isinstance(result, list)

    def test_calculate_quote_with_none_values(self, mock_config, mock_bigquery_client):
        """Should handle None values in rate data."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=45000,
                total_7nights_single=None,  # None value
                total_7nights_child=None
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            # Should not crash
            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=2
            )

            assert result is not None


# ==================== Additional Initialization Tests ====================

class TestBigQueryToolInitExtended:
    """Extended initialization tests for BigQueryTool."""

    def test_init_stores_project_id_from_config(self, mock_config):
        """Should store project ID from config on successful init."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            assert tool.project_id == "test-project"
            assert tool.config.gcp_project_id == "test-project"

    def test_init_missing_gcp_project_uses_config_value(self):
        """Should pass config gcp_project_id to BigQuery Client."""
        config = MagicMock()
        config.client_id = "custom_tenant"
        config.gcp_project_id = "custom-gcp-project-id"

        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(config)

            mock_bq.Client.assert_called_once_with(project="custom-gcp-project-id")

    def test_init_client_none_on_error_does_not_set_project_id(self, mock_config):
        """When client init fails, client should be None."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.side_effect = Exception("Credentials not found")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            assert tool.client is None
            # config is still stored
            assert tool.config == mock_config


# ==================== DatabaseTables Table Name Tests ====================

class TestDatabaseTablesIntegration:
    """Test that BigQueryTool uses DatabaseTables for table name resolution."""

    def test_find_matching_hotels_uses_db_hotel_rates_table(self, mock_config, mock_bigquery_client):
        """SQL query should reference the db.hotel_rates table name."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            # The query text should contain the hotel_rates table reference
            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "hotel_rates" in call_args

    def test_get_flight_price_uses_db_flight_prices_table(self, mock_config, mock_bigquery_client):
        """SQL query should reference the db.flight_prices table name."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = iter([])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.get_flight_price("Mauritius", "2024-06-01")

            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "flight_prices" in call_args

    def test_get_next_consultant_uses_db_consultants_table(self, mock_config, mock_bigquery_client):
        """SQL query should reference the db.consultants table name."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client

            query_job = MagicMock()
            query_job.result.return_value = iter([])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.get_next_consultant_round_robin()

            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "consultants" in call_args


# ==================== Extended Hotel Search Tests ====================

class TestFindMatchingHotelsExtended:
    """Extended tests for find_matching_hotels covering SQL construction and filtering."""

    def test_query_includes_is_active_filter(self, mock_config, mock_bigquery_client):
        """SQL should filter by is_active = TRUE."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "is_active = TRUE" in call_args

    def test_query_includes_nights_filter(self, mock_config, mock_bigquery_client):
        """SQL should filter by nights parameter."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_matching_hotels(
                destination="Zanzibar",
                check_in="2024-07-01",
                check_out="2024-07-08",
                nights=7,
                adults=2
            )

            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "r.nights = @nights" in call_args

    def test_query_has_deduplication_qualify_clause(self, mock_config, mock_bigquery_client):
        """SQL should have QUALIFY deduplication clause."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "QUALIFY ROW_NUMBER()" in call_args

    def test_query_has_limit_50(self, mock_config, mock_bigquery_client):
        """SQL should limit results to 50."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "LIMIT 50" in call_args

    def test_query_without_meal_plan_does_not_have_meal_plan_param(self, mock_config, mock_bigquery_client):
        """SQL should not include meal_plan filter when not specified."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2,
                meal_plan_pref=None
            )

            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "r.meal_plan = @meal_plan" not in call_args

    def test_destination_search_terms_uppercased(self, mock_config, mock_bigquery_client):
        """Destination search terms should be uppercased for case-insensitive matching."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            mock_config.get_destination_search_terms.return_value = ["mauritius", "mu"]

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_matching_hotels(
                destination="mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            # ArrayQueryParameter should have been called with uppercased destinations
            mock_bq.ArrayQueryParameter.assert_called_once()
            array_call_args = mock_bq.ArrayQueryParameter.call_args
            assert array_call_args[0][0] == "destinations"
            assert array_call_args[0][2] == ["MAURITIUS", "MU"]

    def test_find_matching_hotels_returns_list_of_dicts(self, mock_config, mock_bigquery_client, sample_hotel_results):
        """Returned hotels should be a list of dictionaries."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = sample_hotel_results
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            assert isinstance(result, list)
            for item in result:
                assert isinstance(item, dict)


# ==================== Extended Rate Lookup Tests ====================

class TestFindRatesByHotelNamesExtended:
    """Extended tests for find_rates_by_hotel_names."""

    def test_multiple_hotels_generate_or_conditions(self, mock_config, mock_bigquery_client):
        """Multiple hotel names should generate OR'd LIKE conditions."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_rates_by_hotel_names(
                hotel_names=["Diamonds Leisure Beach", "Serena Beach Hotel"],
                nights=7,
                check_in="2024-06-01",
                check_out="2024-06-08"
            )

            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "OR" in call_args

    def test_find_rates_query_has_limit_100(self, mock_config, mock_bigquery_client):
        """SQL should have LIMIT 100."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_rates_by_hotel_names(
                hotel_names=["Solana Beach"],
                nights=7,
                check_in="2024-06-01",
                check_out="2024-06-08"
            )

            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "LIMIT 100" in call_args

    def test_find_rates_handles_query_error(self, mock_config, mock_bigquery_client):
        """Should return empty list on query error."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_bigquery_client.query.side_effect = Exception("Timeout")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.find_rates_by_hotel_names(
                hotel_names=["Test Hotel"],
                nights=7,
                check_in="2024-06-01",
                check_out="2024-06-08"
            )

            assert result == []


# ==================== Extended Price Calculation Tests ====================

class TestCalculateQuotePriceExtended:
    """Extended price calculation tests."""

    def test_calculate_quote_grand_total_two_adults_sharing(self, mock_config, mock_bigquery_client):
        """Grand total for 2 adults sharing should be 2 * per-person-sharing."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=40000,
                total_7nights_single=55000,
                total_7nights_child=20000
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=2
            )

            assert result['totals']['grand_total'] == 80000  # 2 * 40000
            assert result['totals']['adults'] == 80000

    def test_calculate_quote_mixed_children_and_infants(self, mock_config, mock_bigquery_client):
        """Should correctly separate children (2-12) from infants (<2)."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=40000,
                total_7nights_single=55000,
                total_7nights_child=20000
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=2,
                children_ages=[1, 5, 10, 0]  # 2 infants (age 0, 1), 2 children (age 5, 10)
            )

            assert result['traveler_counts']['infants'] == 2
            assert result['traveler_counts']['children'] == 2
            assert result['totals']['infants'] == 2000  # 2 * 1000 flat rate
            assert result['totals']['children'] == 40000  # 2 * 20000

    def test_calculate_quote_single_adult_uses_single_rate(self, mock_config, mock_bigquery_client):
        """Single adult with no children should use single room rate."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=40000,
                total_7nights_single=55000,
                total_7nights_child=20000
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=1
            )

            assert result['totals']['grand_total'] == 55000  # single rate
            assert result['per_person_rates']['adult_single'] == 55000

    def test_calculate_quote_mixed_rooms_total(self, mock_config, mock_bigquery_client):
        """Mixed rooms: 1 single + 2 sharing should total correctly."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=40000,
                total_7nights_single=55000,
                total_7nights_child=20000
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=3,
                single_adults=1
            )

            # 2 sharing * 40000 + 1 single * 55000 = 135000
            assert result['totals']['adults'] == 135000
            assert result['totals']['grand_total'] == 135000

    def test_calculate_quote_single_with_none_single_rate_falls_back(self, mock_config, mock_bigquery_client):
        """When single rate is None, should fall back to sharing rate for single traveler."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=40000,
                total_7nights_single=None,
                total_7nights_child=None
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=1
            )

            # Falls back to pps rate when single is None
            assert result['per_person_rates']['adult_single'] == 40000
            assert result['totals']['grand_total'] == 40000

    def test_calculate_quote_handles_query_exception(self, mock_config, mock_bigquery_client):
        """Should return None when query throws an exception."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_bigquery_client.query.side_effect = Exception("Connection timeout")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=2
            )

            assert result is None

    def test_calculate_quote_breakdown_keys_present(self, mock_config, mock_bigquery_client):
        """Result should contain all expected breakdown keys."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=45000,
                total_7nights_single=52000,
                total_7nights_child=22000
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=2
            )

            assert 'breakdown' in result
            assert 'adult_hotel' in result['breakdown']
            assert 'child_hotel' in result['breakdown']
            assert 'flight_pp' in result['breakdown']


# ==================== Extended Hotel Name Normalization Tests ====================

class TestHotelNameNormalizationExtended:
    """Extended tests for hotel name normalization and keyword extraction."""

    def test_normalize_removes_unicode_stars(self, mock_config):
        """Should replace unicode star characters."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool._normalize_hotel_name("4\u2605 Serena Beach Hotel")
            assert "\u2605" not in result

    def test_normalize_strips_whitespace(self, mock_config):
        """Should strip leading/trailing whitespace."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool._normalize_hotel_name("  Beach Resort  ")
            assert result == result.strip()

    def test_extract_keywords_returns_distinctive_words(self, mock_config):
        """Should return distinctive brand words, filtering generics."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            keywords = tool._extract_hotel_keywords("Diamonds Leisure Beach & Golf Resort")
            assert "diamonds" in keywords
            assert "leisure" in keywords
            assert "golf" in keywords
            # Common words filtered
            assert "beach" not in keywords
            assert "resort" not in keywords

    def test_extract_keywords_filters_short_words(self, mock_config):
        """Words with 2 or fewer characters should be filtered out."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = MagicMock()

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            keywords = tool._extract_hotel_keywords("SBH Hotel at Bay")
            # "at" is both common and short, "sbh" is exactly 3 chars so included
            assert "sbh" in keywords


# ==================== Extended Consultant Tests ====================

class TestConsultantRoundRobinExtended:
    """Extended tests for consultant round-robin assignment."""

    def test_consultant_updates_last_assigned(self, mock_config, mock_bigquery_client):
        """Should update last_assigned timestamp after selection."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client

            mock_consultant = MagicMock(
                consultant_id="C001",
                name="Alice Smith",
                email="alice@example.com"
            )
            # First query returns consultant, second is the UPDATE
            query_job_select = MagicMock()
            query_job_select.result.return_value = iter([mock_consultant])
            query_job_update = MagicMock()
            query_job_update.result.return_value = None

            mock_bigquery_client.query.side_effect = [query_job_select, query_job_update]

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_next_consultant_round_robin()

            assert result is not None
            # Should have called query twice: SELECT + UPDATE
            assert mock_bigquery_client.query.call_count == 2

    def test_consultant_update_failure_still_returns_consultant(self, mock_config, mock_bigquery_client):
        """Should still return consultant even if update fails."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client

            mock_consultant = MagicMock(
                consultant_id="C001",
                name="Bob Jones",
                email="bob@example.com"
            )
            query_job_select = MagicMock()
            query_job_select.result.return_value = iter([mock_consultant])

            # First call succeeds (SELECT), second raises (UPDATE)
            call_count = [0]
            def query_side_effect(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] == 1:
                    return query_job_select
                raise Exception("Update failed")

            mock_bigquery_client.query.side_effect = query_side_effect

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_next_consultant_round_robin()

            # Should still return the consultant despite update failure
            assert result is not None


# ==================== Extended Search Hotels Tests ====================

class TestSearchHotelsByNameExtended:
    """Extended tests for search_hotels_by_name."""

    def test_search_hotels_query_uses_like_pattern(self, mock_config, mock_bigquery_client):
        """Search term should be wrapped in % wildcards for LIKE."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.search_hotels_by_name("Serena")

            # ScalarQueryParameter should be called with %Serena% pattern
            calls = mock_bq.ScalarQueryParameter.call_args_list
            search_param_found = False
            for call in calls:
                if call[0][0] == "search_term" and "%Serena%" in str(call[0][2]):
                    search_param_found = True
            assert search_param_found

    def test_search_hotels_handles_exception(self, mock_config, mock_bigquery_client):
        """Should return empty list on exception."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_bigquery_client.query.side_effect = Exception("Network error")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.search_hotels_by_name("Test")

            assert result == []

    def test_search_hotels_default_limit_is_5(self, mock_config, mock_bigquery_client):
        """Default limit parameter should be 5."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.search_hotels_by_name("Resort")

            # Check that the limit parameter was passed as 5
            calls = mock_bq.ScalarQueryParameter.call_args_list
            limit_param_found = False
            for call in calls:
                if call[0][0] == "limit" and call[0][2] == 5:
                    limit_param_found = True
            assert limit_param_found


# ==================== Extended Get Hotel Info Tests ====================

class TestGetHotelInfoExtended:
    """Extended tests for get_hotel_info."""

    def test_get_hotel_info_query_has_limit_1(self, mock_config, mock_bigquery_client):
        """Query should have LIMIT 1 to return single hotel."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = iter([])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.get_hotel_info("Solana Beach")

            call_args = mock_bigquery_client.query.call_args[0][0]
            assert "LIMIT 1" in call_args

    def test_get_hotel_info_handles_exception(self, mock_config, mock_bigquery_client):
        """Should return None on exception."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_bigquery_client.query.side_effect = Exception("Timeout error")

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_hotel_info("Test Hotel")

            assert result is None


# ==================== Extended Query Timeout Tests ====================

class TestQueryTimeoutExtended:
    """Extended timeout tests."""

    def test_find_rates_by_hotel_names_has_timeout(self, mock_config, mock_bigquery_client):
        """find_rates_by_hotel_names should use 8 second timeout."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            tool.find_rates_by_hotel_names(
                hotel_names=["Solana Beach"],
                nights=7,
                check_in="2024-06-01",
                check_out="2024-06-08"
            )

            query_job.result.assert_called_with(timeout=8.0)

    def test_timeout_exception_returns_empty_list(self, mock_config, mock_bigquery_client):
        """Timeout during find_matching_hotels should return empty list."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.side_effect = Exception("Deadline exceeded: 8.0 seconds")
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.find_matching_hotels(
                destination="Mauritius",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            assert result == []


# ==================== Extended Edge Cases ====================

class TestEdgeCasesExtended:
    """Extended edge case and error handling tests."""

    def test_find_rates_with_only_common_word_hotel_names(self, mock_config, mock_bigquery_client):
        """Hotel names with only common words should still extract some keywords or handle gracefully."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            # "The Hotel" has only common/short words
            result = tool.find_rates_by_hotel_names(
                hotel_names=["The Hotel"],
                nights=7,
                check_in="2024-06-01",
                check_out="2024-06-08"
            )

            # Should not crash, returns empty list (no valid keywords)
            assert isinstance(result, list)

    def test_calculate_quote_zero_price_rates(self, mock_config, mock_bigquery_client):
        """Should handle zero-priced rates without error."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_rate = MagicMock(
                total_7nights_pps=0,
                total_7nights_single=0,
                total_7nights_child=0
            )
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_rate])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.calculate_quote_price(
                rate_id="RATE001",
                adults=2
            )

            assert result is not None
            assert result['totals']['grand_total'] == 0

    def test_find_matching_hotels_empty_results(self, mock_config, mock_bigquery_client):
        """Should return empty list when no results match."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ArrayQueryParameter = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            query_job = MagicMock()
            query_job.result.return_value = []
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.find_matching_hotels(
                destination="NonexistentDestination",
                check_in="2024-06-01",
                check_out="2024-06-08",
                nights=7,
                adults=2
            )

            assert result == []

    def test_get_flight_price_returns_integer(self, mock_config, mock_bigquery_client):
        """Flight price should always be returned as int."""
        with patch('src.tools.bigquery_tool.bigquery') as mock_bq:
            mock_bq.Client.return_value = mock_bigquery_client
            mock_bq.QueryJobConfig.return_value = MagicMock()
            mock_bq.ScalarQueryParameter = MagicMock()

            mock_flight = MagicMock(price_per_person=15500.75)
            query_job = MagicMock()
            query_job.result.return_value = iter([mock_flight])
            mock_bigquery_client.query.return_value = query_job

            from src.tools.bigquery_tool import BigQueryTool
            tool = BigQueryTool(mock_config)

            result = tool.get_flight_price("Mauritius", "2024-06-01")

            assert isinstance(result, int)
            assert result == 15500
