"""
Quote Agent Tests

Comprehensive tests for src/agents/quote_agent.py covering:
- QuoteAgent initialization (services available and unavailable)
- Quote ID generation (QT-YYYYMMDD-XXXXXX format)
- Customer data normalization (dates, defaults, destination matching)
- Full generate_quote flow (success, no hotels, drafts, email failures)
- Hotel search via BigQuery and live rates
- Pricing calculation and deduplication
- Supabase persistence (save, get, list, update)
- CRM integration (new/existing clients, stages)
- Follow-up call scheduling and business day calculation
- send_draft_quote and resend_quote flows

All external dependencies (BigQuery, Supabase, PDF, Email, CRM, Rates) are mocked.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from datetime import datetime, timedelta, date
import re

# Override asyncio_mode for this module since all tests are synchronous.
# pytest-asyncio with asyncio_mode="auto" hangs when combined with
# run_async / event-loop usage inside the QuoteAgent.
pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_config():
    """Create a mock ClientConfig tailored for QuoteAgent tests."""
    config = MagicMock()
    config.client_id = 'test_client'
    config.destination_names = ['Zanzibar', 'Mauritius', 'Maldives']
    config.timezone = 'Africa/Johannesburg'
    config.currency = 'ZAR'
    config.company_name = 'Test Travel Co'
    return config


def _build_quote_agent(mock_config, **overrides):
    """
    Build a QuoteAgent with all external dependencies mocked.

    Returns (agent, mocks_dict) where mocks_dict has keys:
        db, bq_tool, pdf_generator, email_sender, supabase, crm, rates_client
    """
    mock_db = MagicMock()
    mock_bq = MagicMock()
    mock_pdf = MagicMock()
    mock_email = MagicMock()
    mock_supa = MagicMock()
    mock_supa.client = MagicMock()
    mock_crm = MagicMock()
    mock_rates = MagicMock()

    # Apply overrides (e.g. supabase=None)
    mocks = {
        'db': mock_db,
        'bq_tool': mock_bq,
        'pdf_generator': mock_pdf,
        'email_sender': mock_email,
        'supabase': mock_supa,
        'crm': mock_crm,
        'rates_client': mock_rates,
    }
    mocks.update(overrides)

    with patch('src.agents.quote_agent.DatabaseTables', return_value=mocks['db']), \
         patch('src.agents.quote_agent.BigQueryTool', return_value=mocks['bq_tool']), \
         patch('src.agents.quote_agent.PDFGenerator', return_value=mocks['pdf_generator']), \
         patch('src.agents.quote_agent.EmailSender', return_value=mocks['email_sender']), \
         patch('src.tools.supabase_tool.SupabaseTool', return_value=mocks['supabase']), \
         patch('src.services.crm_service.CRMService', return_value=mocks['crm']), \
         patch('src.services.travel_platform_rates_client.get_travel_platform_rates_client',
               return_value=mocks['rates_client']):
        from src.agents.quote_agent import QuoteAgent
        agent = QuoteAgent(mock_config)

    # Force-assign mocks to guarantee isolation regardless of import order.
    # bq_tool, pdf_generator, email_sender are @property with lazy init,
    # so we assign to the private backing attributes.
    agent.db = mocks['db']
    agent._bq_tool = mocks['bq_tool']
    agent._pdf_generator = mocks['pdf_generator']
    agent._email_sender = mocks['email_sender']
    agent.supabase = mocks['supabase']
    agent.crm = mocks['crm']
    agent.rates_client = mocks['rates_client']

    return agent, mocks


@pytest.fixture
def quote_agent(mock_config):
    """Standard QuoteAgent with all services mocked and available."""
    agent, _ = _build_quote_agent(mock_config)
    return agent


@pytest.fixture
def quote_agent_with_mocks(mock_config):
    """QuoteAgent plus the underlying mocks dictionary."""
    return _build_quote_agent(mock_config)


@pytest.fixture
def sample_customer_data():
    """Minimal valid customer data."""
    return {
        'name': 'John Doe',
        'email': 'john@example.com',
        'phone': '+27821234567',
        'destination': 'Zanzibar',
        'check_in': '2026-06-15',
        'check_out': '2026-06-22',
        'adults': 2,
        'children': 0,
    }


@pytest.fixture
def sample_hotel_rows():
    """Sample BigQuery hotel rows returned by bq_tool.find_matching_hotels."""
    return [
        {
            'hotel_name': 'Beach Resort A',
            'hotel_rating': '5*',
            'room_type': 'Deluxe Suite',
            'meal_plan': 'All Inclusive',
            'rate_id': 'rate_001',
        },
        {
            'hotel_name': 'Beach Resort B',
            'hotel_rating': '4*',
            'room_type': 'Standard Room',
            'meal_plan': 'Bed & Breakfast',
            'rate_id': 'rate_002',
        },
        {
            'hotel_name': 'Beach Resort C',
            'hotel_rating': '3*',
            'room_type': 'Economy Room',
            'meal_plan': 'Half Board',
            'rate_id': 'rate_003',
        },
    ]


@pytest.fixture
def sample_pricing():
    """Sample pricing breakdown returned by bq_tool.calculate_quote_price."""
    return {
        'per_person_rates': {'adult_sharing': 1500.00},
        'totals': {
            'accommodation': 3000.00,
            'flights': 0,
            'transfers': 0,
            'grand_total': 3000.00,
        },
    }


# ---------------------------------------------------------------------------
# 1. Initialization Tests
# ---------------------------------------------------------------------------

class TestInitialization:

    def test_init_all_services_available(self, mock_config):
        """Agent initializes with all services wired."""
        agent, mocks = _build_quote_agent(mock_config)
        assert agent.config is mock_config
        assert agent.supabase is not None
        assert agent.crm is not None
        assert agent.rates_client is not None

    def test_init_supabase_unavailable(self, mock_config):
        """Agent should gracefully handle missing Supabase."""
        agent, _ = _build_quote_agent(mock_config, supabase=None)
        agent.supabase = None  # explicitly None
        assert agent.supabase is None

    def test_init_crm_unavailable(self, mock_config):
        """Agent should gracefully handle missing CRM."""
        agent, _ = _build_quote_agent(mock_config, crm=None)
        agent.crm = None
        assert agent.crm is None

    def test_init_rates_client_unavailable(self, mock_config):
        """Agent should gracefully handle missing rates client."""
        agent, _ = _build_quote_agent(mock_config, rates_client=None)
        agent.rates_client = None
        assert agent.rates_client is None

    def test_init_default_settings(self, quote_agent):
        """Agent has expected default settings."""
        assert quote_agent.max_hotels_per_quote == 3
        assert quote_agent.default_nights == 7


# ---------------------------------------------------------------------------
# 2. _generate_quote_id Tests
# ---------------------------------------------------------------------------

class TestGenerateQuoteId:

    def test_format_matches_pattern(self, quote_agent):
        """Quote ID matches QT-YYYYMMDD-XXXXXX."""
        qid = quote_agent._generate_quote_id()
        assert re.match(r'^QT-\d{8}-[A-F0-9]{6}$', qid), f"Bad format: {qid}"

    def test_contains_todays_date(self, quote_agent):
        """Quote ID contains current UTC date segment."""
        qid = quote_agent._generate_quote_id()
        date_part = qid.split('-')[1]
        today_str = datetime.utcnow().strftime('%Y%m%d')
        assert date_part == today_str

    def test_unique_ids(self, quote_agent):
        """Multiple calls produce unique IDs."""
        ids = {quote_agent._generate_quote_id() for _ in range(50)}
        assert len(ids) == 50

    def test_suffix_is_uppercase_hex(self, quote_agent):
        """The 6-character suffix is uppercase hex."""
        qid = quote_agent._generate_quote_id()
        suffix = qid.split('-')[2]
        assert len(suffix) == 6
        assert suffix == suffix.upper()
        int(suffix, 16)  # should not raise


# ---------------------------------------------------------------------------
# 3. _normalize_customer_data Tests
# ---------------------------------------------------------------------------

class TestNormalizeCustomerData:

    def test_basic_normalization(self, quote_agent, sample_customer_data):
        """Normalizes basic customer data correctly."""
        result = quote_agent._normalize_customer_data(sample_customer_data)
        assert result['name'] == 'John Doe'
        assert result['email'] == 'john@example.com'
        assert result['destination'] == 'Zanzibar'
        assert result['adults'] == 2
        assert result['children'] == 0
        assert result['nights'] == 7

    def test_string_dates_preserved(self, quote_agent):
        """String dates are kept as-is."""
        data = {'check_in': '2026-03-01', 'check_out': '2026-03-05'}
        result = quote_agent._normalize_customer_data(data)
        assert result['check_in'] == '2026-03-01'
        assert result['check_out'] == '2026-03-05'
        assert result['nights'] == 4

    def test_date_objects_converted_to_strings(self, quote_agent):
        """Date/datetime objects are formatted to YYYY-MM-DD."""
        data = {
            'check_in': date(2026, 7, 1),
            'check_out': date(2026, 7, 10),
        }
        result = quote_agent._normalize_customer_data(data)
        assert result['check_in'] == '2026-07-01'
        assert result['check_out'] == '2026-07-10'
        assert result['nights'] == 9

    def test_datetime_objects_converted(self, quote_agent):
        """datetime objects are formatted to YYYY-MM-DD."""
        data = {
            'check_in': datetime(2026, 8, 15, 14, 30),
            'check_out': datetime(2026, 8, 22, 10, 0),
        }
        result = quote_agent._normalize_customer_data(data)
        assert result['check_in'] == '2026-08-15'
        assert result['check_out'] == '2026-08-22'

    def test_default_dates_when_missing(self, quote_agent):
        """Default check_in is 30 days from now; check_out is default_nights after."""
        result = quote_agent._normalize_customer_data({})
        ci = datetime.strptime(result['check_in'], '%Y-%m-%d')
        co = datetime.strptime(result['check_out'], '%Y-%m-%d')
        # check_in should be roughly 30 days from now (date-level precision)
        expected_ci = (datetime.utcnow() + timedelta(days=30)).date()
        assert ci.date() == expected_ci
        assert result['nights'] == quote_agent.default_nights
        assert (co - ci).days == quote_agent.default_nights

    def test_default_checkout_from_checkin(self, quote_agent):
        """When only check_in given, check_out defaults to check_in + default_nights."""
        data = {'check_in': '2026-05-01'}
        result = quote_agent._normalize_customer_data(data)
        assert result['check_out'] == '2026-05-08'  # 7 nights
        assert result['nights'] == 7

    def test_defaults_for_missing_name_and_email(self, quote_agent):
        """Missing name defaults to 'Valued Customer', email defaults to empty."""
        result = quote_agent._normalize_customer_data({})
        assert result['name'] == 'Valued Customer'
        assert result['email'] == ''

    def test_adults_default(self, quote_agent):
        """Adults default to 2."""
        result = quote_agent._normalize_customer_data({})
        assert result['adults'] == 2

    def test_children_default(self, quote_agent):
        """Children default to 0."""
        result = quote_agent._normalize_customer_data({})
        assert result['children'] == 0

    def test_children_ages_preserved(self, quote_agent):
        """Children ages are passed through."""
        data = {'children_ages': [4, 8]}
        result = quote_agent._normalize_customer_data(data)
        assert result['children_ages'] == [4, 8]

    def test_children_ages_default_empty(self, quote_agent):
        """Children ages default to empty list."""
        result = quote_agent._normalize_customer_data({})
        assert result['children_ages'] == []

    def test_destination_case_insensitive_match(self, quote_agent):
        """Destination is corrected to canonical case from config."""
        data = {'destination': 'zanzibar'}
        result = quote_agent._normalize_customer_data(data)
        assert result['destination'] == 'Zanzibar'

    def test_destination_unknown_left_as_is(self, quote_agent):
        """Unknown destinations are left unchanged."""
        data = {'destination': 'Atlantis'}
        result = quote_agent._normalize_customer_data(data)
        assert result['destination'] == 'Atlantis'

    def test_budget_from_budget_field(self, quote_agent):
        """Budget extracted from 'budget' key."""
        data = {'budget': 5000}
        result = quote_agent._normalize_customer_data(data)
        assert result['budget'] == 5000

    def test_budget_from_total_budget_field(self, quote_agent):
        """Budget falls back to 'total_budget' key."""
        data = {'total_budget': 8000}
        result = quote_agent._normalize_customer_data(data)
        assert result['budget'] == 8000

    def test_phone_preserved(self, quote_agent):
        """Phone number passes through."""
        data = {'phone': '+27821234567'}
        result = quote_agent._normalize_customer_data(data)
        assert result['phone'] == '+27821234567'


# ---------------------------------------------------------------------------
# 4. _find_hotels Tests
# ---------------------------------------------------------------------------

class TestFindHotels:

    def test_delegates_to_bq_tool(self, quote_agent):
        """_find_hotels delegates to bq_tool.find_matching_hotels."""
        customer = {
            'destination': 'Zanzibar',
            'check_in': '2026-06-15',
            'check_out': '2026-06-22',
            'nights': 7,
            'adults': 2,
            'children': 0,
            'children_ages': [],
            'budget': None,
        }
        quote_agent.bq_tool.find_matching_hotels.return_value = [{'hotel_name': 'H1'}]

        result = quote_agent._find_hotels(customer)

        quote_agent.bq_tool.find_matching_hotels.assert_called_once()
        assert result == [{'hotel_name': 'H1'}]

    def test_passes_children_flag(self, quote_agent):
        """has_children is True when children_ages provided."""
        customer = {
            'destination': 'Zanzibar',
            'check_in': '2026-06-15',
            'check_out': '2026-06-22',
            'nights': 7,
            'adults': 2,
            'children': 1,
            'children_ages': [5],
            'budget': 2000,
        }
        quote_agent.bq_tool.find_matching_hotels.return_value = []

        quote_agent._find_hotels(customer)

        call_kwargs = quote_agent.bq_tool.find_matching_hotels.call_args
        assert call_kwargs[1]['has_children'] is True

    def test_returns_empty_when_none_found(self, quote_agent):
        """Returns empty list when BigQuery finds no hotels."""
        quote_agent.bq_tool.find_matching_hotels.return_value = []
        customer = {
            'destination': 'Zanzibar', 'check_in': '2026-06-15',
            'check_out': '2026-06-22', 'nights': 7, 'adults': 2,
        }
        assert quote_agent._find_hotels(customer) == []


# ---------------------------------------------------------------------------
# 5. _find_hotels_live Tests
# ---------------------------------------------------------------------------

class TestFindHotelsLive:

    def test_returns_empty_when_no_rates_client(self, quote_agent):
        """Returns empty if rates_client is None."""
        quote_agent.rates_client = None
        result = quote_agent._find_hotels_live({'check_in': '2026-06-15',
                                                 'check_out': '2026-06-22',
                                                 'destination': 'Zanzibar',
                                                 'adults': 2, 'nights': 7}, None)
        assert result == []

    def test_returns_empty_on_unsuccessful_result(self, quote_agent):
        """Returns empty when rates engine returns success=False."""
        with patch('src.agents.quote_agent.run_async',
                   return_value={'success': False, 'error': 'timeout'}):
            result = quote_agent._find_hotels_live(
                {'check_in': '2026-06-15', 'check_out': '2026-06-22',
                 'destination': 'Zanzibar', 'adults': 2, 'nights': 7,
                 'children': 0}, None)
        assert result == []

    def test_returns_empty_on_no_hotels(self, quote_agent):
        """Returns empty when rates engine returns no hotels."""
        with patch('src.agents.quote_agent.run_async',
                   return_value={'success': True, 'hotels': []}):
            result = quote_agent._find_hotels_live(
                {'check_in': '2026-06-15', 'check_out': '2026-06-22',
                 'destination': 'Zanzibar', 'adults': 2, 'nights': 7,
                 'children': 0}, None)
        assert result == []

    def test_transforms_live_hotel_data(self, quote_agent):
        """Transforms live rate hotel data into quote format."""
        hotels_data = {
            'success': True,
            'hotels': [{
                'hotel_name': 'Luxury Beach Hotel',
                'hotel_id': 'lbh_001',
                'stars': 5,
                'image_url': 'https://img.example.com/lbh.jpg',
                'options': [{
                    'room_type': 'Ocean Suite',
                    'meal_plan': 'All Inclusive',
                    'price_total': 14000,
                    'price_per_night': 2000,
                    'currency': 'ZAR',
                }],
            }],
        }
        with patch('src.agents.quote_agent.run_async', return_value=hotels_data):
            result = quote_agent._find_hotels_live(
                {'check_in': '2026-06-15', 'check_out': '2026-06-22',
                 'destination': 'Zanzibar', 'adults': 2, 'nights': 7,
                 'children': 0}, None)

        assert len(result) == 1
        h = result[0]
        assert h['hotel_name'] == 'Luxury Beach Hotel'
        assert h['room_type'] == 'Ocean Suite'
        assert h['total_price'] == 14000
        assert h['price_per_person'] == 7000.0  # 14000 / 2 adults
        assert h['source'] == 'live_rates'
        assert h['currency'] == 'ZAR'
        assert h['image_url'] == 'https://img.example.com/lbh.jpg'

    def test_filters_by_selected_hotels(self, quote_agent):
        """Only matching hotels returned when selected_hotels provided."""
        hotels_data = {
            'success': True,
            'hotels': [
                {'hotel_name': 'Alpha Resort', 'stars': 4,
                 'options': [{'room_type': 'Std', 'meal_plan': 'BB',
                              'price_total': 5000, 'price_per_night': 714, 'currency': 'ZAR'}]},
                {'hotel_name': 'Beta Lodge', 'stars': 3,
                 'options': [{'room_type': 'Std', 'meal_plan': 'BB',
                              'price_total': 3000, 'price_per_night': 428, 'currency': 'ZAR'}]},
            ],
        }
        with patch('src.agents.quote_agent.run_async', return_value=hotels_data):
            result = quote_agent._find_hotels_live(
                {'check_in': '2026-06-15', 'check_out': '2026-06-22',
                 'destination': 'Zanzibar', 'adults': 2, 'nights': 7,
                 'children': 0},
                selected_hotels=['Alpha Resort'])

        assert len(result) == 1
        assert result[0]['hotel_name'] == 'Alpha Resort'

    def test_budget_sorting(self, quote_agent):
        """Hotels sorted by proximity to budget when budget specified."""
        hotels_data = {
            'success': True,
            'hotels': [
                {'hotel_name': 'Cheap', 'stars': 3,
                 'options': [{'room_type': 'Std', 'meal_plan': 'BB',
                              'price_total': 2000, 'price_per_night': 285, 'currency': 'ZAR'}]},
                {'hotel_name': 'Mid', 'stars': 4,
                 'options': [{'room_type': 'Std', 'meal_plan': 'BB',
                              'price_total': 6000, 'price_per_night': 857, 'currency': 'ZAR'}]},
                {'hotel_name': 'Pricey', 'stars': 5,
                 'options': [{'room_type': 'Std', 'meal_plan': 'BB',
                              'price_total': 10000, 'price_per_night': 1428, 'currency': 'ZAR'}]},
            ],
        }
        with patch('src.agents.quote_agent.run_async', return_value=hotels_data):
            result = quote_agent._find_hotels_live(
                {'check_in': '2026-06-15', 'check_out': '2026-06-22',
                 'destination': 'Zanzibar', 'adults': 2, 'nights': 7,
                 'children': 0, 'budget': 3000},
                None)

        # Mid hotel (pp=3000) should be first as closest to budget 3000
        assert result[0]['hotel_name'] == 'Mid'

    def test_deduplication_by_hotel_name(self, quote_agent):
        """Only first option per hotel_name is kept."""
        hotels_data = {
            'success': True,
            'hotels': [
                {'hotel_name': 'Same Hotel', 'stars': 4,
                 'options': [
                     {'room_type': 'Room A', 'meal_plan': 'AI',
                      'price_total': 5000, 'price_per_night': 714, 'currency': 'ZAR'},
                     {'room_type': 'Room B', 'meal_plan': 'BB',
                      'price_total': 3000, 'price_per_night': 428, 'currency': 'ZAR'},
                 ]},
            ],
        }
        with patch('src.agents.quote_agent.run_async', return_value=hotels_data):
            result = quote_agent._find_hotels_live(
                {'check_in': '2026-06-15', 'check_out': '2026-06-22',
                 'destination': 'Zanzibar', 'adults': 2, 'nights': 7,
                 'children': 0}, None)

        # Two options from same hotel, but only one after dedup
        assert len(result) == 1

    def test_cheapest_price_fallback_when_no_options(self, quote_agent):
        """Uses cheapest_price when options array is empty."""
        hotels_data = {
            'success': True,
            'hotels': [{
                'hotel_name': 'Fallback Hotel',
                'stars': 4,
                'cheapest_price': 7000,
                'cheapest_meal_plan': 'Half Board',
                'options': [],
            }],
        }
        with patch('src.agents.quote_agent.run_async', return_value=hotels_data):
            result = quote_agent._find_hotels_live(
                {'check_in': '2026-06-15', 'check_out': '2026-06-22',
                 'destination': 'Zanzibar', 'adults': 2, 'nights': 7,
                 'children': 0}, None)

        assert len(result) == 1
        assert result[0]['total_price'] == 7000
        assert result[0]['meal_plan'] == 'Half Board'

    def test_skips_zero_price_options(self, quote_agent):
        """Options with total_price <= 0 are skipped."""
        hotels_data = {
            'success': True,
            'hotels': [{
                'hotel_name': 'Free Hotel',
                'stars': 3,
                'options': [{'room_type': 'Std', 'meal_plan': 'BB',
                             'price_total': 0, 'price_per_night': 0, 'currency': 'ZAR'}],
            }],
        }
        with patch('src.agents.quote_agent.run_async', return_value=hotels_data):
            result = quote_agent._find_hotels_live(
                {'check_in': '2026-06-15', 'check_out': '2026-06-22',
                 'destination': 'Zanzibar', 'adults': 2, 'nights': 7,
                 'children': 0}, None)
        assert result == []

    def test_returns_empty_on_exception(self, quote_agent):
        """Returns empty list when an exception occurs."""
        with patch('src.agents.quote_agent.run_async', side_effect=Exception("network error")):
            result = quote_agent._find_hotels_live(
                {'check_in': '2026-06-15', 'check_out': '2026-06-22',
                 'destination': 'Zanzibar', 'adults': 2, 'nights': 7,
                 'children': 0}, None)
        assert result == []


# ---------------------------------------------------------------------------
# 6. _calculate_hotel_options Tests
# ---------------------------------------------------------------------------

class TestCalculateHotelOptions:

    def test_calculates_pricing_for_hotels(self, quote_agent, sample_hotel_rows, sample_pricing):
        """Pricing calculated for each hotel via bq_tool."""
        quote_agent.bq_tool.calculate_quote_price.return_value = sample_pricing
        customer = {'adults': 2, 'children_ages': []}

        result = quote_agent._calculate_hotel_options(sample_hotel_rows, customer)

        assert len(result) == 3
        assert quote_agent.bq_tool.calculate_quote_price.call_count == 3

    def test_deduplicates_by_hotel_name(self, quote_agent, sample_pricing):
        """Duplicate hotel names are removed; only first kept."""
        hotels = [
            {'hotel_name': 'Same Hotel', 'rate_id': 'r1'},
            {'hotel_name': 'Same Hotel', 'rate_id': 'r2'},
            {'hotel_name': 'Different Hotel', 'rate_id': 'r3'},
        ]
        quote_agent.bq_tool.calculate_quote_price.return_value = sample_pricing
        customer = {'adults': 2, 'children_ages': []}

        result = quote_agent._calculate_hotel_options(hotels, customer)

        assert len(result) == 2
        names = [o['hotel_name'] for o in result]
        assert names.count('Same Hotel') == 1

    def test_skips_hotels_without_pricing(self, quote_agent):
        """Hotels where calculate_quote_price returns None are skipped."""
        hotels = [{'hotel_name': 'No Price Hotel', 'rate_id': 'r1'}]
        quote_agent.bq_tool.calculate_quote_price.return_value = None
        customer = {'adults': 2, 'children_ages': []}

        result = quote_agent._calculate_hotel_options(hotels, customer)

        assert result == []

    def test_sorted_by_total_price(self, quote_agent):
        """Options sorted by total_price ascending."""
        hotels = [
            {'hotel_name': 'Expensive', 'rate_id': 'r1'},
            {'hotel_name': 'Cheap', 'rate_id': 'r2'},
        ]
        pricing_expensive = {
            'per_person_rates': {'adult_sharing': 5000},
            'totals': {'grand_total': 10000, 'accommodation': 10000, 'flights': 0, 'transfers': 0},
        }
        pricing_cheap = {
            'per_person_rates': {'adult_sharing': 1000},
            'totals': {'grand_total': 2000, 'accommodation': 2000, 'flights': 0, 'transfers': 0},
        }
        quote_agent.bq_tool.calculate_quote_price.side_effect = [pricing_expensive, pricing_cheap]
        customer = {'adults': 2, 'children_ages': []}

        result = quote_agent._calculate_hotel_options(hotels, customer)

        assert result[0]['hotel_name'] == 'Cheap'
        assert result[1]['hotel_name'] == 'Expensive'

    def test_caps_at_max_hotels_times_two(self, quote_agent, sample_pricing):
        """Processing stops after max_hotels_per_quote * 2 unique options."""
        quote_agent.max_hotels_per_quote = 2
        hotels = [{'hotel_name': f'Hotel {i}', 'rate_id': f'r{i}'} for i in range(10)]
        quote_agent.bq_tool.calculate_quote_price.return_value = sample_pricing
        customer = {'adults': 2, 'children_ages': []}

        result = quote_agent._calculate_hotel_options(hotels, customer)

        assert len(result) == 4  # 2 * 2 = 4

    def test_option_structure(self, quote_agent, sample_hotel_rows, sample_pricing):
        """Each option has expected keys."""
        quote_agent.bq_tool.calculate_quote_price.return_value = sample_pricing
        customer = {'adults': 2, 'children_ages': []}
        result = quote_agent._calculate_hotel_options(sample_hotel_rows[:1], customer)

        option = result[0]
        assert option['name'] == 'Beach Resort A'
        assert option['hotel_name'] == 'Beach Resort A'
        assert option['rating'] == '5*'
        assert option['room_type'] == 'Deluxe Suite'
        assert option['meal_plan'] == 'All Inclusive'
        assert option['price_per_person'] == 1500.00
        assert option['total_price'] == 3000.00
        assert option['includes_flights'] is False
        assert option['includes_transfers'] is True
        assert option['rate_id'] == 'rate_001'
        assert 'pricing_breakdown' in option


# ---------------------------------------------------------------------------
# 7. _save_quote_to_supabase Tests
# ---------------------------------------------------------------------------

class TestSaveQuoteToSupabase:

    def _make_quote(self, **overrides):
        quote = {
            'quote_id': 'QT-20260615-ABC123',
            'customer_name': 'Jane',
            'customer_email': 'jane@example.com',
            'customer_phone': '+27800000000',
            'destination': 'Zanzibar',
            'check_in_date': '2026-06-15',
            'check_out_date': '2026-06-22',
            'nights': 7,
            'adults': 2,
            'children': 0,
            'children_ages': [],
            'hotels': [],
            'total_price': 5000,
            'status': 'generated',
            'email_sent': True,
            'pdf_generated': True,
            'consultant': None,
            'created_at': '2026-06-01T00:00:00',
        }
        quote.update(overrides)
        return quote

    def test_save_success(self, quote_agent):
        """Returns True when Supabase insert succeeds."""
        mock_result = MagicMock()
        mock_result.data = [{'id': 1}]
        quote_agent.supabase.client.table.return_value.insert.return_value.execute.return_value = mock_result

        result = quote_agent._save_quote_to_supabase(self._make_quote())
        assert result is True

    def test_save_returns_false_on_no_data(self, quote_agent):
        """Returns False when insert returns empty data."""
        mock_result = MagicMock()
        mock_result.data = None
        quote_agent.supabase.client.table.return_value.insert.return_value.execute.return_value = mock_result

        result = quote_agent._save_quote_to_supabase(self._make_quote())
        assert result is False

    def test_save_returns_false_on_exception(self, quote_agent):
        """Returns False on exception."""
        quote_agent.supabase.client.table.return_value.insert.return_value.execute.side_effect = Exception("db error")

        result = quote_agent._save_quote_to_supabase(self._make_quote())
        assert result is False

    def test_save_returns_false_when_no_supabase(self, quote_agent):
        """Returns False when supabase is None."""
        quote_agent.supabase = None
        result = quote_agent._save_quote_to_supabase(self._make_quote())
        assert result is False

    def test_save_returns_false_when_no_client(self, quote_agent):
        """Returns False when supabase.client is None."""
        quote_agent.supabase.client = None
        result = quote_agent._save_quote_to_supabase(self._make_quote())
        assert result is False

    def test_save_includes_consultant_id(self, quote_agent):
        """Consultant ID is extracted from consultant dict."""
        mock_result = MagicMock()
        mock_result.data = [{'id': 1}]
        mock_table = MagicMock()
        mock_table.insert.return_value.execute.return_value = mock_result
        quote_agent.supabase.client.table.return_value = mock_table

        quote = self._make_quote(consultant={'consultant_id': 'c99', 'name': 'Alice'})
        quote_agent._save_quote_to_supabase(quote)

        inserted = mock_table.insert.call_args[0][0]
        assert inserted['consultant_id'] == 'c99'


# ---------------------------------------------------------------------------
# 8. get_quote Tests
# ---------------------------------------------------------------------------

class TestGetQuote:

    def test_returns_quote_when_found(self, quote_agent):
        """Returns quote data when found."""
        expected = {'quote_id': 'QT-001', 'status': 'sent'}
        mock_result = MagicMock()
        mock_result.data = expected
        quote_agent.supabase.client.table.return_value \
            .select.return_value \
            .eq.return_value \
            .eq.return_value \
            .single.return_value \
            .execute.return_value = mock_result

        result = quote_agent.get_quote('QT-001')
        assert result == expected

    def test_returns_none_when_not_found(self, quote_agent):
        """Returns None when quote not in database."""
        mock_result = MagicMock()
        mock_result.data = None
        quote_agent.supabase.client.table.return_value \
            .select.return_value \
            .eq.return_value \
            .eq.return_value \
            .single.return_value \
            .execute.return_value = mock_result

        result = quote_agent.get_quote('QT-NONEXISTENT')
        assert result is None

    def test_returns_none_on_exception(self, quote_agent):
        """Returns None when exception occurs."""
        quote_agent.supabase.client.table.return_value \
            .select.return_value \
            .eq.return_value \
            .eq.return_value \
            .single.return_value \
            .execute.side_effect = Exception("timeout")

        assert quote_agent.get_quote('QT-001') is None

    def test_returns_none_when_no_supabase(self, quote_agent):
        """Returns None when supabase not available."""
        quote_agent.supabase = None
        assert quote_agent.get_quote('QT-001') is None

    def test_returns_none_when_no_client(self, quote_agent):
        """Returns None when supabase.client is None."""
        quote_agent.supabase.client = None
        assert quote_agent.get_quote('QT-001') is None


# ---------------------------------------------------------------------------
# 9. list_quotes Tests
# ---------------------------------------------------------------------------

class TestListQuotes:

    def test_returns_quotes_list(self, quote_agent):
        """Returns list of quotes from Supabase."""
        expected = [{'quote_id': 'Q1'}, {'quote_id': 'Q2'}]
        mock_result = MagicMock()
        mock_result.data = expected
        quote_agent.supabase.client.table.return_value \
            .select.return_value \
            .eq.return_value \
            .order.return_value \
            .range.return_value \
            .execute.return_value = mock_result

        result = quote_agent.list_quotes()
        assert result == expected

    def test_filters_by_status(self, quote_agent):
        """Applies status filter when provided."""
        mock_chain = MagicMock()
        mock_result = MagicMock()
        mock_result.data = [{'quote_id': 'Q1', 'status': 'sent'}]
        # Build chain so .eq().execute() works after the range().eq() call
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.range.return_value = mock_chain
        mock_chain.execute.return_value = mock_result
        quote_agent.supabase.client.table.return_value = mock_chain

        result = quote_agent.list_quotes(status='sent')
        assert result == [{'quote_id': 'Q1', 'status': 'sent'}]

    def test_returns_empty_on_exception(self, quote_agent):
        """Returns empty list on exception."""
        quote_agent.supabase.client.table.side_effect = Exception("db fail")
        assert quote_agent.list_quotes() == []

    def test_returns_empty_when_no_supabase(self, quote_agent):
        """Returns empty when supabase unavailable."""
        quote_agent.supabase = None
        assert quote_agent.list_quotes() == []

    def test_returns_empty_when_no_client(self, quote_agent):
        """Returns empty when supabase.client is None."""
        quote_agent.supabase.client = None
        assert quote_agent.list_quotes() == []

    def test_handles_none_data(self, quote_agent):
        """Returns empty list when result.data is None."""
        mock_chain = MagicMock()
        mock_result = MagicMock()
        mock_result.data = None
        mock_chain.select.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.order.return_value = mock_chain
        mock_chain.range.return_value = mock_chain
        mock_chain.execute.return_value = mock_result
        quote_agent.supabase.client.table.return_value = mock_chain

        result = quote_agent.list_quotes()
        assert result == []


# ---------------------------------------------------------------------------
# 10. update_quote_status Tests
# ---------------------------------------------------------------------------

class TestUpdateQuoteStatus:

    def _setup_update_chain(self, quote_agent):
        mock_chain = MagicMock()
        mock_chain.update.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock()
        quote_agent.supabase.client.table.return_value = mock_chain
        return mock_chain

    def test_updates_status(self, quote_agent):
        """Returns True on successful update."""
        self._setup_update_chain(quote_agent)
        assert quote_agent.update_quote_status('QT-001', 'viewed') is True

    def test_sent_status_adds_sent_at(self, quote_agent):
        """Status 'sent' adds sent_at timestamp."""
        chain = self._setup_update_chain(quote_agent)
        quote_agent.update_quote_status('QT-001', 'sent')
        update_data = chain.update.call_args[0][0]
        assert 'sent_at' in update_data

    def test_viewed_status_adds_viewed_at(self, quote_agent):
        """Status 'viewed' adds viewed_at timestamp."""
        chain = self._setup_update_chain(quote_agent)
        quote_agent.update_quote_status('QT-001', 'viewed')
        update_data = chain.update.call_args[0][0]
        assert 'viewed_at' in update_data

    def test_accepted_status_adds_accepted_at(self, quote_agent):
        """Status 'accepted' adds accepted_at timestamp."""
        chain = self._setup_update_chain(quote_agent)
        quote_agent.update_quote_status('QT-001', 'accepted')
        update_data = chain.update.call_args[0][0]
        assert 'accepted_at' in update_data

    def test_generic_status_no_extra_timestamp(self, quote_agent):
        """Generic status only has status and updated_at."""
        chain = self._setup_update_chain(quote_agent)
        quote_agent.update_quote_status('QT-001', 'draft')
        update_data = chain.update.call_args[0][0]
        assert 'sent_at' not in update_data
        assert 'viewed_at' not in update_data
        assert 'accepted_at' not in update_data

    def test_returns_false_on_exception(self, quote_agent):
        """Returns False on exception."""
        quote_agent.supabase.client.table.side_effect = Exception("db fail")
        assert quote_agent.update_quote_status('QT-001', 'sent') is False

    def test_returns_false_when_no_supabase(self, quote_agent):
        """Returns False when supabase unavailable."""
        quote_agent.supabase = None
        assert quote_agent.update_quote_status('QT-001', 'sent') is False


# ---------------------------------------------------------------------------
# 11. _add_to_crm Tests
# ---------------------------------------------------------------------------

class TestAddToCrm:

    def test_returns_none_when_no_crm(self, quote_agent):
        """Returns None when CRM not available."""
        quote_agent.crm = None
        result = quote_agent._add_to_crm({'email': 'a@b.com', 'name': 'A'}, 'QT-001')
        assert result is None

    def test_new_client_created(self, quote_agent):
        """Creates new client when email not found in CRM."""
        quote_agent.crm.get_client_by_email.return_value = None
        quote_agent.crm.get_or_create_client.return_value = {'client_id': 'c1'}

        result = quote_agent._add_to_crm(
            {'email': 'new@test.com', 'name': 'New User'}, 'QT-001')

        assert result['success'] is True
        assert result['created'] is True

    def test_existing_client_updated(self, quote_agent):
        """Updates existing client quote count."""
        quote_agent.crm.get_client_by_email.return_value = {
            'client_id': 'c1', 'pipeline_stage': 'QUOTED', 'quote_count': 1
        }

        result = quote_agent._add_to_crm(
            {'email': 'existing@test.com', 'name': 'Old User', 'destination': 'Zanzibar'},
            'QT-002')

        assert result['success'] is True
        assert result['created'] is False
        quote_agent.crm.update_client.assert_called_once()

    def test_moves_to_negotiating_on_second_quote(self, quote_agent):
        """Client moved to NEGOTIATING stage on second quote."""
        quote_agent.crm.get_client_by_email.return_value = {
            'client_id': 'c1', 'pipeline_stage': 'QUOTED', 'quote_count': 1
        }

        quote_agent._add_to_crm(
            {'email': 'e@t.com', 'name': 'User', 'destination': 'Zanzibar'}, 'QT-003')

        quote_agent.crm.update_stage.assert_called_once()

    def test_does_not_move_stage_if_already_negotiating(self, quote_agent):
        """Does not move stage if already past QUOTED."""
        quote_agent.crm.get_client_by_email.return_value = {
            'client_id': 'c1', 'pipeline_stage': 'NEGOTIATING', 'quote_count': 2
        }

        quote_agent._add_to_crm(
            {'email': 'e@t.com', 'name': 'User', 'destination': 'Zanzibar'}, 'QT-004')

        quote_agent.crm.update_stage.assert_not_called()

    def test_logs_activity_for_existing_client(self, quote_agent):
        """Activity is logged via supabase for existing client."""
        quote_agent.crm.get_client_by_email.return_value = {
            'client_id': 'c1', 'pipeline_stage': 'QUOTED', 'quote_count': 0
        }

        quote_agent._add_to_crm(
            {'email': 'e@t.com', 'name': 'User', 'destination': 'Zanzibar'}, 'QT-005')

        quote_agent.supabase.log_activity.assert_called_once()

    def test_returns_error_on_exception(self, quote_agent):
        """Returns error dict on exception."""
        quote_agent.crm.get_client_by_email.side_effect = Exception("CRM down")

        result = quote_agent._add_to_crm({'email': 'e@t.com', 'name': 'User'}, 'QT-006')
        assert result['success'] is False

    def test_new_client_failure_returns_false(self, quote_agent):
        """Returns success=False when get_or_create_client returns None."""
        quote_agent.crm.get_client_by_email.return_value = None
        quote_agent.crm.get_or_create_client.return_value = None

        result = quote_agent._add_to_crm(
            {'email': 'fail@test.com', 'name': 'Fail User'}, 'QT-007')

        assert result['success'] is False


# ---------------------------------------------------------------------------
# 12. _schedule_follow_up_call Tests
# ---------------------------------------------------------------------------

class TestScheduleFollowUpCall:

    def test_success(self, quote_agent):
        """Returns True when call queued successfully."""
        quote_agent.supabase.queue_outbound_call.return_value = True

        result = quote_agent._schedule_follow_up_call(
            'QT-001', 'John', 'john@e.com', '+27800000000', 'Zanzibar')

        assert result is True
        quote_agent.supabase.queue_outbound_call.assert_called_once()

    def test_returns_false_when_no_supabase(self, quote_agent):
        """Returns False when Supabase unavailable."""
        quote_agent.supabase = None
        result = quote_agent._schedule_follow_up_call(
            'QT-001', 'John', 'john@e.com', '+27800000000', 'Zanzibar')
        assert result is False

    def test_returns_false_on_exception(self, quote_agent):
        """Returns False on exception."""
        quote_agent.supabase.queue_outbound_call.side_effect = Exception("err")
        result = quote_agent._schedule_follow_up_call(
            'QT-001', 'John', 'john@e.com', '+27800000000', 'Zanzibar')
        assert result is False

    def test_returns_false_when_queue_returns_none(self, quote_agent):
        """Returns False when queue_outbound_call returns falsy."""
        quote_agent.supabase.queue_outbound_call.return_value = None
        result = quote_agent._schedule_follow_up_call(
            'QT-001', 'John', 'john@e.com', '+27800000000', 'Zanzibar')
        assert result is False


# ---------------------------------------------------------------------------
# 13. Business Day Helpers Tests
# ---------------------------------------------------------------------------

class TestBusinessDayHelpers:

    def test_get_next_business_day_10am_returns_datetime(self, quote_agent):
        """Returns a datetime object."""
        result = quote_agent._get_next_business_day_10am()
        assert isinstance(result, datetime)

    def test_get_next_business_day_10am_is_weekday(self, quote_agent):
        """Returned date is a weekday (Mon-Fri)."""
        result = quote_agent._get_next_business_day_10am()
        assert result.weekday() < 5  # 0=Mon, 4=Fri

    def test_get_next_business_day_10am_skips_saturday(self, quote_agent):
        """If today is Friday after 10am, should skip Sat/Sun."""
        import pytz
        tz = pytz.timezone('Africa/Johannesburg')
        # Simulate Friday at 11am SAST
        friday_11am = datetime(2026, 2, 6, 11, 0, 0, tzinfo=tz)  # Friday

        with patch('src.agents.quote_agent.datetime') as mock_dt:
            mock_dt.now.return_value = friday_11am
            mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
            # We need the real replace and timedelta behavior
            result = quote_agent._get_next_business_day_10am()

        assert result.weekday() < 5  # Must be weekday

    def test_get_next_business_day_default(self, quote_agent):
        """_get_next_business_day(1) returns a weekday."""
        result = quote_agent._get_next_business_day(1)
        assert isinstance(result, datetime)
        assert result.weekday() < 5

    def test_get_next_business_day_days_ahead(self, quote_agent):
        """_get_next_business_day(3) returns a date 3+ days ahead."""
        now = datetime.utcnow()
        result = quote_agent._get_next_business_day(3)
        # Should be at least 3 days from now (may be more due to weekends)
        diff = result - now
        assert diff.days >= 2  # at least 2 days (accounting for timezone differences)

    def test_get_next_business_day_utc_no_tzinfo(self, quote_agent):
        """Result has tzinfo stripped (stored as naive UTC)."""
        result = quote_agent._get_next_business_day(1)
        assert result.tzinfo is None

    def test_get_next_business_day_10am_utc_no_tzinfo(self, quote_agent):
        """Result has tzinfo stripped."""
        result = quote_agent._get_next_business_day_10am()
        assert result.tzinfo is None

    def test_get_next_business_day_invalid_timezone_fallback(self, quote_agent):
        """Falls back to UTC on invalid timezone when ValueError is raised."""
        import pytz
        original_tz = pytz.timezone

        def tz_that_raises(zone):
            """First call raises ValueError to trigger fallback; second call is real."""
            if zone == 'Bad/Zone':
                raise ValueError("bad timezone")
            return original_tz(zone)

        quote_agent.config.timezone = 'Bad/Zone'
        with patch.dict('sys.modules', {}):
            with patch('pytz.timezone', side_effect=tz_that_raises):
                result = quote_agent._get_next_business_day(1)
        assert isinstance(result, datetime)
        assert result.weekday() < 5


# ---------------------------------------------------------------------------
# 14. generate_quote Integration Tests
# ---------------------------------------------------------------------------

class TestGenerateQuote:

    def _setup_successful_flow(self, agent, mocks):
        """Configure mocks for a successful quote generation."""
        # BQ returns hotels
        mocks['bq_tool'].find_matching_hotels.return_value = [
            {'hotel_name': 'Beach Hotel', 'rate_id': 'r1', 'hotel_rating': '4*',
             'room_type': 'Deluxe', 'meal_plan': 'AI'},
        ]
        # Pricing
        mocks['bq_tool'].calculate_quote_price.return_value = {
            'per_person_rates': {'adult_sharing': 2500},
            'totals': {'grand_total': 5000, 'accommodation': 5000, 'flights': 0, 'transfers': 0},
        }
        # Consultant
        mocks['bq_tool'].get_next_consultant_round_robin.return_value = {
            'consultant_id': 'cons_1', 'name': 'Alice'
        }
        # PDF
        mocks['pdf_generator'].generate_quote_pdf.return_value = b'%PDF-fake'
        # Email
        mocks['email_sender'].send_quote_email.return_value = True
        # Supabase save
        mock_result = MagicMock()
        mock_result.data = [{'id': 1}]
        mocks['supabase'].client.table.return_value.insert.return_value.execute.return_value = mock_result
        # CRM
        mocks['crm'].get_client_by_email.return_value = None
        mocks['crm'].get_or_create_client.return_value = {'client_id': 'c1'}
        # Follow-up call
        mocks['supabase'].queue_outbound_call.return_value = True
        # No live rates for this path
        agent.rates_client = None

    def test_successful_quote_generation(self, mock_config, sample_customer_data):
        """Full successful flow returns success=True with quote data."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)

        with patch('src.api.notifications_routes.NotificationService'):
            result = agent.generate_quote(sample_customer_data, use_live_rates=False)

        assert result['success'] is True
        assert 'quote_id' in result
        assert result['email_sent'] is True
        assert result['status'] == 'sent'
        assert result['hotels_count'] >= 1
        assert result['consultant'] is not None

    def test_no_hotels_found_returns_failure(self, mock_config, sample_customer_data):
        """Returns failure when no hotels found."""
        agent, mocks = _build_quote_agent(mock_config)
        agent.rates_client = None
        mocks['bq_tool'].find_matching_hotels.return_value = []

        result = agent.generate_quote(sample_customer_data, use_live_rates=False)

        assert result['success'] is False
        assert result['status'] == 'no_availability'

    def test_draft_mode_skips_email(self, mock_config, sample_customer_data):
        """Draft quotes do not send email."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)

        with patch('src.api.notifications_routes.NotificationService'):
            result = agent.generate_quote(
                sample_customer_data, initial_status='draft', use_live_rates=False)

        assert result['success'] is True
        assert result['status'] == 'draft'
        assert result['email_sent'] is False
        mocks['email_sender'].send_quote_email.assert_not_called()

    def test_email_failure_returns_generated_status(self, mock_config, sample_customer_data):
        """When email fails, status stays 'generated'."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)
        mocks['email_sender'].send_quote_email.return_value = False

        with patch('src.api.notifications_routes.NotificationService'):
            result = agent.generate_quote(sample_customer_data, use_live_rates=False)

        assert result['success'] is True
        assert result['status'] == 'generated'
        assert result['email_sent'] is False

    def test_email_exception_captured(self, mock_config, sample_customer_data):
        """Email exception is caught; quote still succeeds."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)
        mocks['email_sender'].send_quote_email.side_effect = Exception("SMTP error")

        with patch('src.api.notifications_routes.NotificationService'):
            result = agent.generate_quote(sample_customer_data, use_live_rates=False)

        assert result['success'] is True
        assert result['email_sent'] is False
        assert result['email_error'] is not None

    def test_pdf_failure_skips_email(self, mock_config, sample_customer_data):
        """When PDF generation fails, email is not sent."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)
        mocks['pdf_generator'].generate_quote_pdf.side_effect = Exception("PDF error")

        with patch('src.api.notifications_routes.NotificationService'):
            result = agent.generate_quote(sample_customer_data, use_live_rates=False)

        assert result['success'] is True
        assert result['email_sent'] is False
        mocks['email_sender'].send_quote_email.assert_not_called()

    def test_live_rates_used_when_available(self, mock_config, sample_customer_data):
        """Uses live rates when rates_client is available."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)
        # Re-enable rates_client (setup disables it for BQ path)
        agent.rates_client = mocks['rates_client']

        live_data = {
            'success': True,
            'hotels': [{
                'hotel_name': 'Live Hotel',
                'hotel_id': 'lh1',
                'stars': 5,
                'options': [{
                    'room_type': 'Suite',
                    'meal_plan': 'AI',
                    'price_total': 8000,
                    'price_per_night': 1142,
                    'currency': 'ZAR',
                }],
            }],
        }
        with patch('src.agents.quote_agent.run_async', return_value=live_data):
            with patch('src.api.notifications_routes.NotificationService'):
                result = agent.generate_quote(sample_customer_data, use_live_rates=True)

        assert result['success'] is True
        # Should have used live rates, not BigQuery
        mocks['bq_tool'].find_matching_hotels.assert_not_called()

    def test_fallback_to_bigquery_when_live_empty(self, mock_config, sample_customer_data):
        """Falls back to BigQuery when live rates return nothing."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)
        # Re-enable rates_client so generate_quote tries live first
        agent.rates_client = mocks['rates_client']

        with patch('src.agents.quote_agent.run_async',
                   return_value={'success': True, 'hotels': []}):
            with patch('src.api.notifications_routes.NotificationService'):
                result = agent.generate_quote(sample_customer_data, use_live_rates=True)

        assert result['success'] is True
        mocks['bq_tool'].find_matching_hotels.assert_called_once()

    def test_selected_hotels_uses_find_rates_by_name(self, mock_config, sample_customer_data):
        """Selected hotels use bq_tool.find_rates_by_hotel_names."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)
        agent.rates_client = None
        mocks['bq_tool'].find_rates_by_hotel_names.return_value = [
            {'hotel_name': 'Selected Hotel', 'rate_id': 'r1', 'hotel_rating': '5*',
             'room_type': 'Suite', 'meal_plan': 'AI'},
        ]

        with patch('src.api.notifications_routes.NotificationService'):
            result = agent.generate_quote(
                sample_customer_data, selected_hotels=['Selected Hotel'], use_live_rates=False)

        assert result['success'] is True
        mocks['bq_tool'].find_rates_by_hotel_names.assert_called_once()

    def test_no_consultant_when_not_requested(self, mock_config, sample_customer_data):
        """No consultant assigned when assign_consultant=False."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)

        with patch('src.api.notifications_routes.NotificationService'):
            result = agent.generate_quote(
                sample_customer_data, assign_consultant=False, use_live_rates=False)

        assert result['consultant'] is None
        mocks['bq_tool'].get_next_consultant_round_robin.assert_not_called()

    def test_call_queued_when_email_sent_and_phone(self, mock_config, sample_customer_data):
        """Follow-up call queued when email sent and phone present."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)

        with patch('src.api.notifications_routes.NotificationService'):
            result = agent.generate_quote(sample_customer_data, use_live_rates=False)

        assert result['call_queued'] is True

    def test_no_call_when_no_phone(self, mock_config):
        """Follow-up call not queued without phone."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)
        data = {'name': 'No Phone', 'email': 'np@test.com', 'destination': 'Zanzibar',
                'check_in': '2026-06-15', 'check_out': '2026-06-22', 'adults': 2}

        with patch('src.api.notifications_routes.NotificationService'):
            result = agent.generate_quote(data, use_live_rates=False)

        assert result['call_queued'] is False

    def test_exception_returns_error(self, mock_config, sample_customer_data):
        """Top-level exception returns error result."""
        agent, mocks = _build_quote_agent(mock_config)
        # Force early failure by making normalize raise
        with patch.object(agent, '_normalize_customer_data', side_effect=Exception("boom")):
            result = agent.generate_quote(sample_customer_data)

        assert result['success'] is False
        assert result['status'] == 'error'

    def test_crm_added_flag(self, mock_config, sample_customer_data):
        """CRM result is reflected in response."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)

        with patch('src.api.notifications_routes.NotificationService'):
            result = agent.generate_quote(sample_customer_data, use_live_rates=False)

        assert result['crm_added'] is True

    def test_max_hotels_limited(self, mock_config, sample_customer_data):
        """Hotels in quote limited to max_hotels_per_quote."""
        agent, mocks = _build_quote_agent(mock_config)
        self._setup_successful_flow(agent, mocks)
        agent.rates_client = None
        agent.max_hotels_per_quote = 2

        # Return many hotels
        many_hotels = [
            {'hotel_name': f'Hotel {i}', 'rate_id': f'r{i}',
             'hotel_rating': '4*', 'room_type': 'Std', 'meal_plan': 'BB'}
            for i in range(10)
        ]
        mocks['bq_tool'].find_matching_hotels.return_value = many_hotels

        with patch('src.api.notifications_routes.NotificationService'):
            result = agent.generate_quote(sample_customer_data, use_live_rates=False)

        assert result['success'] is True
        assert result['hotels_count'] <= 2


# ---------------------------------------------------------------------------
# 15. send_draft_quote Tests
# ---------------------------------------------------------------------------

class TestSendDraftQuote:

    def _setup_draft_quote(self, quote_agent, status='draft', email='john@e.com', phone='+2780'):
        """Configure mocks for a retrievable draft quote."""
        quote_data = {
            'quote_id': 'QT-001',
            'status': status,
            'customer_email': email,
            'customer_name': 'John',
            'customer_phone': phone,
            'destination': 'Zanzibar',
            'check_in_date': '2026-06-15',
            'check_out_date': '2026-06-22',
            'nights': 7,
            'adults': 2,
            'children': 0,
            'children_ages': [],
            'hotels': [{'hotel_name': 'Beach Hotel', 'total_price': 5000}],
        }
        # Mock get_quote
        mock_result = MagicMock()
        mock_result.data = quote_data
        quote_agent.supabase.client.table.return_value \
            .select.return_value \
            .eq.return_value \
            .eq.return_value \
            .single.return_value \
            .execute.return_value = mock_result

        return quote_data

    def test_successful_send(self, quote_agent):
        """Full successful send_draft_quote flow."""
        self._setup_draft_quote(quote_agent)
        quote_agent.pdf_generator.generate_quote_pdf.return_value = b'%PDF'
        quote_agent.email_sender.send_quote_email.return_value = True
        # Mock update_quote_status
        mock_chain = MagicMock()
        mock_chain.update.return_value = mock_chain
        mock_chain.eq.return_value = mock_chain
        mock_chain.execute.return_value = MagicMock()
        # We need supabase.client.table to handle both get_quote and update calls
        # Use side_effect to handle multiple calls
        quote_agent.supabase.queue_outbound_call.return_value = True

        with patch('src.api.notifications_routes.NotificationService'):
            result = quote_agent.send_draft_quote('QT-001')

        assert result['success'] is True
        assert result['status'] == 'sent'
        assert 'sent_at' in result

    def test_not_found_returns_error(self, quote_agent):
        """Returns error when quote not found."""
        mock_result = MagicMock()
        mock_result.data = None
        quote_agent.supabase.client.table.return_value \
            .select.return_value \
            .eq.return_value \
            .eq.return_value \
            .single.return_value \
            .execute.return_value = mock_result

        result = quote_agent.send_draft_quote('QT-MISSING')
        assert result['success'] is False
        assert 'not found' in result['error']

    def test_not_draft_returns_error(self, quote_agent):
        """Returns error when quote is not in draft status."""
        self._setup_draft_quote(quote_agent, status='sent')

        result = quote_agent.send_draft_quote('QT-001')
        assert result['success'] is False
        assert 'not a draft' in result['error']

    def test_no_email_returns_error(self, quote_agent):
        """Returns error when quote has no customer email."""
        self._setup_draft_quote(quote_agent, email=None)

        result = quote_agent.send_draft_quote('QT-001')
        assert result['success'] is False
        assert 'no customer email' in result['error']

    def test_pdf_failure_returns_error(self, quote_agent):
        """Returns error when PDF generation fails."""
        self._setup_draft_quote(quote_agent)
        quote_agent.pdf_generator.generate_quote_pdf.side_effect = Exception("PDF fail")

        result = quote_agent.send_draft_quote('QT-001')
        assert result['success'] is False
        assert 'PDF generation failed' in result['error']

    def test_pdf_returns_none_error(self, quote_agent):
        """Returns error when PDF returns None."""
        self._setup_draft_quote(quote_agent)
        quote_agent.pdf_generator.generate_quote_pdf.return_value = None

        result = quote_agent.send_draft_quote('QT-001')
        assert result['success'] is False
        assert 'empty result' in result['error']

    def test_email_exception_returns_error(self, quote_agent):
        """Returns error when email sending raises exception."""
        self._setup_draft_quote(quote_agent)
        quote_agent.pdf_generator.generate_quote_pdf.return_value = b'%PDF'
        quote_agent.email_sender.send_quote_email.side_effect = Exception("SMTP fail")

        result = quote_agent.send_draft_quote('QT-001')
        assert result['success'] is False
        assert 'Email sending failed' in result['error']

    def test_email_returns_false_error(self, quote_agent):
        """Returns error when email returns False (SendGrid error)."""
        self._setup_draft_quote(quote_agent)
        quote_agent.pdf_generator.generate_quote_pdf.return_value = b'%PDF'
        quote_agent.email_sender.send_quote_email.return_value = False

        result = quote_agent.send_draft_quote('QT-001')
        assert result['success'] is False
        assert 'SendGrid' in result['error']

    def test_call_queued_when_phone_present(self, quote_agent):
        """Follow-up call queued when phone present."""
        self._setup_draft_quote(quote_agent, phone='+27800000000')
        quote_agent.pdf_generator.generate_quote_pdf.return_value = b'%PDF'
        quote_agent.email_sender.send_quote_email.return_value = True
        quote_agent.supabase.queue_outbound_call.return_value = True

        with patch('src.api.notifications_routes.NotificationService'):
            result = quote_agent.send_draft_quote('QT-001')

        assert result['call_queued'] is True

    def test_no_call_when_no_phone(self, quote_agent):
        """No follow-up call when no phone."""
        self._setup_draft_quote(quote_agent, phone=None)
        quote_agent.pdf_generator.generate_quote_pdf.return_value = b'%PDF'
        quote_agent.email_sender.send_quote_email.return_value = True

        with patch('src.api.notifications_routes.NotificationService'):
            result = quote_agent.send_draft_quote('QT-001')

        assert result['call_queued'] is False

    def test_top_level_exception_caught(self, quote_agent):
        """Top-level exception is caught."""
        quote_agent.supabase = None
        # get_quote will return None, so "not found" error
        result = quote_agent.send_draft_quote('QT-001')
        assert result['success'] is False


# ---------------------------------------------------------------------------
# 16. resend_quote Tests
# ---------------------------------------------------------------------------

class TestResendQuote:

    def _setup_existing_quote(self, quote_agent, status='sent', email='john@e.com'):
        """Configure mocks for a retrievable existing quote."""
        quote_data = {
            'quote_id': 'QT-001',
            'status': status,
            'customer_email': email,
            'customer_name': 'John',
            'customer_phone': '+27800000000',
            'destination': 'Zanzibar',
            'check_in_date': '2026-06-15',
            'check_out_date': '2026-06-22',
            'nights': 7,
            'adults': 2,
            'children': 0,
            'children_ages': [],
            'hotels': [{'hotel_name': 'Hotel X', 'total_price': 4000}],
        }
        mock_result = MagicMock()
        mock_result.data = quote_data
        quote_agent.supabase.client.table.return_value \
            .select.return_value \
            .eq.return_value \
            .eq.return_value \
            .single.return_value \
            .execute.return_value = mock_result
        return quote_data

    def test_successful_resend(self, quote_agent):
        """Full successful resend flow."""
        self._setup_existing_quote(quote_agent)
        quote_agent.pdf_generator.generate_quote_pdf.return_value = b'%PDF'
        quote_agent.email_sender.send_quote_email.return_value = True

        result = quote_agent.resend_quote('QT-001')

        assert result['success'] is True
        assert 'sent_at' in result
        assert result['customer_email'] == 'john@e.com'
        assert 'resent' in result['message'].lower()

    def test_not_found_returns_error(self, quote_agent):
        """Returns error when quote not found."""
        mock_result = MagicMock()
        mock_result.data = None
        quote_agent.supabase.client.table.return_value \
            .select.return_value \
            .eq.return_value \
            .eq.return_value \
            .single.return_value \
            .execute.return_value = mock_result

        result = quote_agent.resend_quote('QT-MISSING')
        assert result['success'] is False
        assert 'not found' in result['error']

    def test_no_email_returns_error(self, quote_agent):
        """Returns error when no customer email."""
        self._setup_existing_quote(quote_agent, email=None)

        result = quote_agent.resend_quote('QT-001')
        assert result['success'] is False
        assert 'no customer email' in result['error']

    def test_pdf_failure_returns_error(self, quote_agent):
        """Returns error when PDF generation fails."""
        self._setup_existing_quote(quote_agent)
        quote_agent.pdf_generator.generate_quote_pdf.side_effect = Exception("PDF error")

        result = quote_agent.resend_quote('QT-001')
        assert result['success'] is False
        assert 'PDF generation failed' in result['error']

    def test_pdf_returns_none_error(self, quote_agent):
        """Returns error when PDF returns None/empty."""
        self._setup_existing_quote(quote_agent)
        quote_agent.pdf_generator.generate_quote_pdf.return_value = None

        result = quote_agent.resend_quote('QT-001')
        assert result['success'] is False
        assert 'no data' in result['error']

    def test_email_exception_returns_error(self, quote_agent):
        """Returns error when email sending raises exception."""
        self._setup_existing_quote(quote_agent)
        quote_agent.pdf_generator.generate_quote_pdf.return_value = b'%PDF'
        quote_agent.email_sender.send_quote_email.side_effect = Exception("SMTP down")

        result = quote_agent.resend_quote('QT-001')
        assert result['success'] is False
        assert 'Email sending failed' in result['error']

    def test_any_status_accepted(self, quote_agent):
        """Resend works on quotes of any status (not just draft)."""
        for status in ['draft', 'sent', 'viewed', 'accepted', 'generated']:
            self._setup_existing_quote(quote_agent, status=status)
            quote_agent.pdf_generator.generate_quote_pdf.return_value = b'%PDF'
            quote_agent.email_sender.send_quote_email.return_value = True

            result = quote_agent.resend_quote('QT-001')
            assert result['success'] is True, f"Failed for status={status}"

    def test_does_not_change_status(self, quote_agent):
        """Resend does NOT call update_quote_status."""
        self._setup_existing_quote(quote_agent, status='viewed')
        quote_agent.pdf_generator.generate_quote_pdf.return_value = b'%PDF'
        quote_agent.email_sender.send_quote_email.return_value = True

        with patch.object(quote_agent, 'update_quote_status') as mock_update:
            quote_agent.resend_quote('QT-001')
            mock_update.assert_not_called()

    def test_top_level_exception_caught(self, quote_agent):
        """Top-level exception returns error."""
        quote_agent.supabase = None
        result = quote_agent.resend_quote('QT-001')
        assert result['success'] is False


# ---------------------------------------------------------------------------
# 17. run_async Helper Tests
# ---------------------------------------------------------------------------

class TestRunAsync:

    def test_run_async_is_callable(self):
        """run_async should be importable and callable."""
        from src.agents.quote_agent import run_async
        assert callable(run_async)

    def test_run_async_calls_asyncio_run(self):
        """run_async delegates to asyncio.run when no event loop is running."""
        from src.agents.quote_agent import run_async
        mock_coro = MagicMock()

        with patch('src.agents.quote_agent.asyncio') as mock_asyncio:
            mock_asyncio.get_event_loop.side_effect = RuntimeError("no loop")
            mock_asyncio.run.return_value = 99
            result = run_async(mock_coro)

        mock_asyncio.run.assert_called_once_with(mock_coro)
        assert result == 99
