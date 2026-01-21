"""
BigQuery Mock Infrastructure

Reusable mock classes and data generators for testing BigQuery-dependent code:
- MockBigQueryRow - Simulates BigQuery row objects with attribute access
- MockBigQueryQueryJob - Simulates query job with .result() method
- MockBigQueryClient - Full client mock with query pattern matching
- Data generators for realistic test data

Usage:
    from tests.fixtures.bigquery_fixtures import create_mock_bigquery_client, generate_quotes

    # Create mock client with default empty responses
    mock_client = create_mock_bigquery_client()

    # Set specific response for query patterns
    mock_client.set_response_for_pattern("hotel_rates", generate_hotel_rates(5))
    mock_client.set_response_for_pattern("quotes", generate_quotes(3))

    # Use in tests with patch
    with patch('src.api.analytics_routes.get_bigquery_client_async', return_value=mock_client):
        result = await get_dashboard_all(config)
"""

import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Iterator
from unittest.mock import MagicMock
import random


# ==================== Mock Classes ====================

class MockBigQueryRow:
    """
    Simulates a BigQuery row object with attribute access.

    BigQuery query results return row objects where columns are accessed
    as attributes (e.g., row.hotel_name, row.total_price).

    Args:
        data: Dictionary of column names to values

    Example:
        row = MockBigQueryRow({'hotel_name': 'Resort A', 'total_price': 5000})
        assert row.hotel_name == 'Resort A'
        assert row.total_price == 5000
    """

    def __init__(self, data: Dict[str, Any]):
        self._data = data
        # Set all keys as attributes for direct access
        for key, value in data.items():
            setattr(self, key, value)

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access as well."""
        return self._data.get(key)

    def get(self, key: str, default: Any = None) -> Any:
        """Dict-compatible get method."""
        return self._data.get(key, default)

    def keys(self) -> List[str]:
        """Return column names."""
        return list(self._data.keys())

    def values(self) -> List[Any]:
        """Return column values."""
        return list(self._data.values())

    def items(self):
        """Return key-value pairs."""
        return self._data.items()

    def __repr__(self) -> str:
        return f"MockBigQueryRow({self._data})"


class MockBigQueryQueryJob:
    """
    Simulates a BigQuery QueryJob.

    The query job is returned by client.query() and provides .result()
    to fetch rows with an optional timeout.

    Args:
        rows: List of dictionaries to return as MockBigQueryRow objects

    Attributes:
        call_count: Number of times result() was called
        last_timeout: Last timeout value passed to result()
    """

    def __init__(self, rows: List[Dict[str, Any]] = None):
        self._rows = rows or []
        self.call_count = 0
        self.last_timeout = None

    def result(self, timeout: float = None) -> Iterator[MockBigQueryRow]:
        """
        Return query results as an iterator of MockBigQueryRow objects.

        Args:
            timeout: Query timeout in seconds (tracked but not enforced in mock)

        Returns:
            Iterator of MockBigQueryRow objects
        """
        self.call_count += 1
        self.last_timeout = timeout
        return iter([MockBigQueryRow(row) for row in self._rows])


class MockBigQueryClient:
    """
    Full mock of google.cloud.bigquery.Client.

    Supports:
    - query() method with SQL string capture
    - Pattern-based response matching
    - Query history tracking for assertions

    Args:
        default_response: Default rows to return for unmatched queries

    Example:
        client = MockBigQueryClient()
        client.set_response_for_pattern("hotel_rates", [{'hotel_name': 'A', 'count': 5}])

        job = client.query("SELECT * FROM hotel_rates WHERE...")
        rows = list(job.result())
        assert rows[0].hotel_name == 'A'
    """

    def __init__(self, default_response: List[Dict[str, Any]] = None):
        self._default_response = default_response or []
        self._pattern_responses: Dict[str, List[Dict[str, Any]]] = {}
        self._query_history: List[str] = []
        self.project = "test-project"

    def set_response_for_pattern(self, pattern: str, rows: List[Dict[str, Any]]) -> None:
        """
        Set response data for queries matching a pattern.

        Args:
            pattern: String pattern to match in SQL query (case-insensitive)
            rows: List of dictionaries to return as rows

        Example:
            client.set_response_for_pattern("hotel_rates", generate_hotel_rates(5))
            client.set_response_for_pattern("COUNT(*)", [{'count': 42}])
        """
        self._pattern_responses[pattern.lower()] = rows

    def query(self, sql: str, job_config: Any = None) -> MockBigQueryQueryJob:
        """
        Execute a query and return a MockBigQueryQueryJob.

        Args:
            sql: SQL query string
            job_config: Query job configuration (captured but not used)

        Returns:
            MockBigQueryQueryJob with appropriate response data
        """
        self._query_history.append(sql)
        sql_lower = sql.lower()

        # Find matching pattern
        for pattern, rows in self._pattern_responses.items():
            if pattern in sql_lower:
                return MockBigQueryQueryJob(rows)

        # No match - return default
        return MockBigQueryQueryJob(self._default_response)

    def get_executed_queries(self) -> List[str]:
        """Return list of all executed SQL queries."""
        return self._query_history.copy()

    def get_last_query(self) -> Optional[str]:
        """Return the most recently executed query."""
        return self._query_history[-1] if self._query_history else None

    def clear_history(self) -> None:
        """Clear the query history."""
        self._query_history.clear()


# ==================== Factory Function ====================

def create_mock_bigquery_client(
    default_data: List[Dict[str, Any]] = None,
    preset_patterns: Dict[str, List[Dict[str, Any]]] = None
) -> MockBigQueryClient:
    """
    Create a configured MockBigQueryClient.

    Args:
        default_data: Default response for unmatched queries
        preset_patterns: Dict of pattern -> response data to pre-configure

    Returns:
        Configured MockBigQueryClient instance

    Example:
        # Basic client
        client = create_mock_bigquery_client()

        # Client with hotel/destination counts pre-configured
        client = create_mock_bigquery_client(
            preset_patterns={
                "hotel_count": [{'hotel_count': 150, 'dest_count': 25}],
                "hotel_rates": generate_hotel_rates(10)
            }
        )
    """
    client = MockBigQueryClient(default_data)

    if preset_patterns:
        for pattern, rows in preset_patterns.items():
            client.set_response_for_pattern(pattern, rows)

    return client


# ==================== Data Generators ====================

def generate_hotel_rates(n: int = 5, destination: str = "Mauritius") -> List[Dict[str, Any]]:
    """
    Generate realistic hotel rate records.

    Args:
        n: Number of hotel rates to generate
        destination: Destination for all hotels

    Returns:
        List of hotel rate dictionaries

    Example:
        rates = generate_hotel_rates(5)
        # Returns 5 hotel rate records with realistic pricing
    """
    hotel_names = [
        "Solana Beach Resort",
        "Four Seasons Mauritius",
        "Constance Belle Mare",
        "LUX Grand Gaube",
        "Shangri-La Le Touessrok",
        "One&Only Le Saint Geran",
        "Paradis Beachcomber",
        "The Oberoi Mauritius",
        "Anantara Iko Resort",
        "Heritage Le Telfair",
    ]

    room_types = ["Standard", "Deluxe", "Sea View", "Beach Front", "Suite", "Villa"]
    meal_plans = ["Bed & Breakfast", "Half Board", "Full Board", "All Inclusive"]

    rates = []
    for i in range(n):
        hotel_name = hotel_names[i % len(hotel_names)]
        base_price = random.randint(30000, 80000)

        rates.append({
            "rate_id": f"RATE{str(i+1).zfill(4)}",
            "hotel_name": hotel_name,
            "hotel_rating": random.randint(4, 5),
            "destination": destination,
            "room_type": random.choice(room_types),
            "meal_plan": random.choice(meal_plans),
            "total_7nights_pps": base_price,
            "total_7nights_single": int(base_price * 1.3),
            "total_7nights_child": int(base_price * 0.5),
            "check_in_date": datetime.now().date().isoformat(),
            "check_out_date": (datetime.now() + timedelta(days=7)).date().isoformat(),
            "nights": 7,
            "is_active": True,
            "created_at": datetime.utcnow().isoformat(),
        })

    return rates


def generate_quotes(
    n: int = 3,
    statuses: List[str] = None,
    tenant_id: str = "test_tenant"
) -> List[Dict[str, Any]]:
    """
    Generate realistic quote records.

    Args:
        n: Number of quotes to generate
        statuses: List of statuses to cycle through (default: accepted, sent, draft)
        tenant_id: Tenant ID for all quotes

    Returns:
        List of quote dictionaries

    Example:
        quotes = generate_quotes(5, statuses=['accepted', 'sent', 'draft'])
    """
    if statuses is None:
        statuses = ["accepted", "sent", "draft"]

    destinations = ["Maldives", "Mauritius", "Seychelles", "Bali", "Thailand", "Sri Lanka"]
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Edward", "Fiona"]
    last_names = ["Doe", "Smith", "Wilson", "Johnson", "Brown", "Taylor", "Miller", "Davis"]

    quotes = []
    for i in range(n):
        first = random.choice(first_names)
        last = random.choice(last_names)
        destination = random.choice(destinations)
        created_at = datetime.utcnow() - timedelta(days=random.randint(0, 30))
        status = statuses[i % len(statuses)]

        hotels_data = [
            {
                "name": f"Resort {chr(65 + i)}",
                "hotel_name": f"Resort {chr(65 + i)}",
                "total_price": random.randint(2000, 5000)
            }
        ]

        quotes.append({
            "quote_id": f"QT-{created_at.strftime('%Y%m%d')}-{str(i+1).zfill(3)}",
            "tenant_id": tenant_id,
            "customer_name": f"{first} {last}",
            "customer_email": f"{first.lower()}.{last.lower()}@example.com",
            "destination": destination,
            "total_price": random.randint(3000, 15000),
            "status": status,
            "created_at": created_at.isoformat(),
            "updated_at": created_at.isoformat(),
            "hotels": hotels_data,  # Can be list or JSON string
            "start_date": (created_at + timedelta(days=30)).date().isoformat(),
            "end_date": (created_at + timedelta(days=37)).date().isoformat(),
            "adults": random.randint(1, 4),
            "children": random.randint(0, 2),
        })

    return quotes


def generate_invoices(
    n: int = 3,
    statuses: List[str] = None,
    tenant_id: str = "test_tenant"
) -> List[Dict[str, Any]]:
    """
    Generate realistic invoice records.

    Args:
        n: Number of invoices to generate
        statuses: List of statuses to cycle through (default: paid, sent, draft)
        tenant_id: Tenant ID for all invoices

    Returns:
        List of invoice dictionaries with varying due dates for aging tests

    Example:
        invoices = generate_invoices(5)
        # Includes mix of current, 30-day, 60-day, and 90+ day overdue invoices
    """
    if statuses is None:
        statuses = ["paid", "sent", "draft"]

    first_names = ["John", "Jane", "Bob", "Alice", "Charlie"]
    last_names = ["Doe", "Smith", "Wilson", "Johnson", "Brown"]

    # Varied due dates for aging tests
    due_date_offsets = [
        30,   # Future - current
        -5,   # Slightly overdue - current
        -15,  # 30 days bucket
        -45,  # 60 days bucket
        -100, # 90+ days bucket
    ]

    invoices = []
    now = datetime.utcnow()

    for i in range(n):
        first = random.choice(first_names)
        last = random.choice(last_names)
        created_at = now - timedelta(days=random.randint(0, 60))
        status = statuses[i % len(statuses)]

        # Vary due dates for aging distribution
        due_offset = due_date_offsets[i % len(due_date_offsets)]
        due_date = now + timedelta(days=due_offset)

        invoices.append({
            "invoice_id": f"INV-{created_at.strftime('%Y%m%d')}-{str(i+1).zfill(3)}",
            "tenant_id": tenant_id,
            "customer_name": f"{first} {last}",
            "customer_email": f"{first.lower()}.{last.lower()}@example.com",
            "total_amount": random.randint(1000, 10000),
            "status": status,
            "due_date": due_date.isoformat(),
            "created_at": created_at.isoformat(),
            "paid_at": created_at.isoformat() if status == "paid" else None,
            "quote_id": f"QT-{created_at.strftime('%Y%m%d')}-{str(i+1).zfill(3)}",
        })

    return invoices


def generate_call_records(
    n: int = 5,
    outcomes: List[str] = None,
    tenant_id: str = "test_tenant"
) -> List[Dict[str, Any]]:
    """
    Generate realistic call record data.

    Args:
        n: Number of call records to generate
        outcomes: List of outcomes to cycle through
        tenant_id: Tenant ID for all records

    Returns:
        List of call record dictionaries

    Example:
        calls = generate_call_records(10)
        # Mix of completed, failed, no_answer outcomes
    """
    if outcomes is None:
        outcomes = ["completed", "voicemail", "no_answer", "busy", "failed"]

    statuses = {
        "completed": "completed",
        "voicemail": "completed",
        "no_answer": "failed",
        "busy": "failed",
        "failed": "failed",
    }

    records = []
    now = datetime.utcnow()

    for i in range(n):
        outcome = outcomes[i % len(outcomes)]
        call_status = statuses.get(outcome, "completed")
        created_at = now - timedelta(days=random.randint(0, 30), hours=random.randint(0, 23))

        duration = random.randint(30, 300) if call_status == "completed" else 0

        records.append({
            "call_id": f"CALL-{str(i+1).zfill(4)}",
            "tenant_id": tenant_id,
            "call_status": call_status,
            "status": call_status,  # Some tables use 'status' instead of 'call_status'
            "outcome": outcome,
            "duration_seconds": duration,
            "duration": duration,  # Some tables use 'duration'
            "created_at": created_at.isoformat(),
            "client_id": f"client_{i+1}",
            "phone_number": f"+1555000{str(i+1).zfill(4)}",
        })

    return records


def generate_call_queue(
    n: int = 5,
    tenant_id: str = "test_tenant"
) -> List[Dict[str, Any]]:
    """
    Generate outbound call queue records.

    Args:
        n: Number of queue records to generate
        tenant_id: Tenant ID for all records

    Returns:
        List of call queue dictionaries with mixed statuses
    """
    queue_statuses = ["queued", "scheduled", "in_progress", "queued", "scheduled"]

    records = []
    now = datetime.utcnow()

    for i in range(n):
        status = queue_statuses[i % len(queue_statuses)]
        scheduled_at = now + timedelta(hours=random.randint(1, 48)) if status == "scheduled" else None

        records.append({
            "queue_id": f"QUEUE-{str(i+1).zfill(4)}",
            "tenant_id": tenant_id,
            "call_status": status,
            "status": status,
            "scheduled_at": scheduled_at.isoformat() if scheduled_at else None,
            "created_at": now.isoformat(),
            "client_id": f"client_{i+1}",
            "phone_number": f"+1555000{str(i+1).zfill(4)}",
            "priority": random.randint(1, 5),
        })

    return records


def generate_clients(
    n: int = 5,
    stages: List[str] = None,
    tenant_id: str = "test_tenant"
) -> List[Dict[str, Any]]:
    """
    Generate realistic CRM client records.

    Args:
        n: Number of clients to generate
        stages: Pipeline stages to cycle through
        tenant_id: Tenant ID for all clients

    Returns:
        List of client dictionaries

    Example:
        clients = generate_clients(10)
        # Mix of pipeline stages
    """
    if stages is None:
        stages = ["QUOTED", "NEGOTIATING", "BOOKED", "PAID", "TRAVELLED", "LOST"]

    sources = ["website", "referral", "social_media", "phone", "email", "walk_in"]
    first_names = ["John", "Jane", "Bob", "Alice", "Charlie", "Diana", "Edward", "Fiona"]
    last_names = ["Doe", "Smith", "Wilson", "Johnson", "Brown", "Taylor", "Miller", "Davis"]

    clients = []
    now = datetime.utcnow()

    for i in range(n):
        first = random.choice(first_names)
        last = random.choice(last_names)
        created_at = now - timedelta(days=random.randint(0, 90))
        stage = stages[i % len(stages)]

        clients.append({
            "client_id": f"client_{i+1}",
            "tenant_id": tenant_id,
            "name": f"{first} {last}",
            "email": f"{first.lower()}.{last.lower()}@example.com",
            "phone": f"+1555{str(i).zfill(7)}",
            "pipeline_stage": stage,
            "source": random.choice(sources),
            "value": random.randint(1000, 20000),
            "created_at": created_at.isoformat(),
            "updated_at": now.isoformat(),
            "notes": f"Client from {random.choice(sources)}",
        })

    return clients


def generate_activities(
    n: int = 5,
    tenant_id: str = "test_tenant"
) -> List[Dict[str, Any]]:
    """
    Generate recent activity records.

    Args:
        n: Number of activities to generate
        tenant_id: Tenant ID for all activities

    Returns:
        List of activity dictionaries
    """
    activity_types = ["email_sent", "call_made", "quote_created", "invoice_sent", "note_added"]
    descriptions = [
        "Sent follow-up email",
        "Made outbound call",
        "Created new quote",
        "Sent invoice",
        "Added client note",
    ]

    activities = []
    now = datetime.utcnow()

    for i in range(n):
        activity_type = activity_types[i % len(activity_types)]
        created_at = now - timedelta(hours=random.randint(0, 72))

        activities.append({
            "activity_id": f"ACT-{str(i+1).zfill(4)}",
            "tenant_id": tenant_id,
            "activity_type": activity_type,
            "description": descriptions[i % len(descriptions)],
            "client_id": f"client_{random.randint(1, 10)}",
            "created_at": created_at.isoformat(),
            "user_id": f"user_{random.randint(1, 5)}",
        })

    return activities


def generate_dashboard_stats(
    total_quotes: int = 50,
    total_clients: int = 100,
    total_hotels: int = 150,
    total_destinations: int = 25
) -> Dict[str, Any]:
    """
    Generate pre-aggregated dashboard statistics.

    Args:
        total_quotes: Number of quotes
        total_clients: Number of active clients
        total_hotels: Number of hotels in pricing database
        total_destinations: Number of destinations

    Returns:
        Dictionary of dashboard statistics

    Example:
        stats = generate_dashboard_stats(total_quotes=100)
    """
    return {
        "stats": {
            "total_quotes": total_quotes,
            "active_clients": total_clients,
            "total_hotels": total_hotels,
            "total_destinations": total_destinations,
        },
        "recent_quotes": generate_quotes(5),
        "usage": {
            "quotes": {"current": random.randint(0, 20), "limit": 100},
            "api_calls": {"current": random.randint(0, 200), "limit": 1000},
        },
        "generated_at": datetime.utcnow().isoformat(),
    }


def generate_pipeline_summary(
    stages: Dict[str, int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Generate CRM pipeline summary data.

    Args:
        stages: Dict of stage name to count (optional)

    Returns:
        Pipeline summary with counts and values per stage

    Example:
        summary = generate_pipeline_summary()
        # Returns {'QUOTED': {'count': 10, 'value': 50000}, ...}
    """
    if stages is None:
        stages = {
            "QUOTED": 10,
            "NEGOTIATING": 5,
            "BOOKED": 8,
            "PAID": 12,
            "TRAVELLED": 20,
            "LOST": 3,
        }

    summary = {}
    for stage, count in stages.items():
        avg_value = random.randint(3000, 8000)
        summary[stage] = {
            "count": count,
            "value": count * avg_value,
        }

    return summary
