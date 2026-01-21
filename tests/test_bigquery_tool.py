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
