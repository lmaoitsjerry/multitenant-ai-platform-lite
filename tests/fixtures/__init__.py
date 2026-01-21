"""
Test Fixtures Package

Reusable mock infrastructure for external API dependencies:
- BigQuery client mocks and data generators
- SendGrid API mocks and response generators
- (Future) Twilio API mocks
- (Future) LLM/OpenAI mocks

Usage:
    from tests.fixtures.bigquery_fixtures import create_mock_bigquery_client, generate_quotes
    from tests.fixtures.sendgrid_fixtures import create_mock_sendgrid_service, generate_subusers
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

# SendGrid fixtures
from tests.fixtures.sendgrid_fixtures import (
    MockSendGridResponse,
    MockSendGridClient,
    generate_subusers,
    generate_subuser_stats,
    generate_global_stats,
    create_mock_sendgrid_service,
    SUBUSER_LIST_RESPONSE,
    SUBUSER_STATS_RESPONSE,
    GLOBAL_STATS_RESPONSE,
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
    # SendGrid mocks
    "MockSendGridResponse",
    "MockSendGridClient",
    "create_mock_sendgrid_service",
    # SendGrid data generators
    "generate_subusers",
    "generate_subuser_stats",
    "generate_global_stats",
    # SendGrid response templates
    "SUBUSER_LIST_RESPONSE",
    "SUBUSER_STATS_RESPONSE",
    "GLOBAL_STATS_RESPONSE",
]
