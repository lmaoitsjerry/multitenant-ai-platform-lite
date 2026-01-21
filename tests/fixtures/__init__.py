"""
Test Fixtures Package

Reusable mock infrastructure for external API dependencies:
- BigQuery client mocks and data generators
- (Future) SendGrid API mocks
- (Future) Twilio API mocks
- (Future) LLM/OpenAI mocks

Usage:
    from tests.fixtures.bigquery_fixtures import create_mock_bigquery_client, generate_quotes
"""

# BigQuery fixtures
from tests.fixtures.bigquery_fixtures import (
    MockBigQueryRow,
    MockBigQueryQueryJob,
    MockBigQueryClient,
    create_mock_bigquery_client,
    generate_hotel_rates,
    generate_quotes,
    generate_invoices,
    generate_call_records,
    generate_call_queue,
    generate_dashboard_stats,
    generate_clients,
    generate_activities,
    generate_pipeline_summary,
)

__all__ = [
    # BigQuery mocks
    "MockBigQueryRow",
    "MockBigQueryQueryJob",
    "MockBigQueryClient",
    "create_mock_bigquery_client",
    # BigQuery data generators
    "generate_hotel_rates",
    "generate_quotes",
    "generate_invoices",
    "generate_call_records",
    "generate_call_queue",
    "generate_dashboard_stats",
    "generate_clients",
    "generate_activities",
    "generate_pipeline_summary",
]
