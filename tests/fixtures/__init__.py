"""
Test Fixtures Package

Reusable mock infrastructure for external API dependencies:
- BigQuery client mocks and data generators
- SendGrid API mocks and response generators
- Twilio/VAPI API mocks and response generators
- Google GenAI (Gemini) mocks for LLM testing
- GCS (Google Cloud Storage) mocks for file storage testing
- FAISS mocks for vector search testing

Usage:
    from tests.fixtures.bigquery_fixtures import create_mock_bigquery_client, generate_quotes
    from tests.fixtures.sendgrid_fixtures import create_mock_sendgrid_service, generate_subusers
    from tests.fixtures.twilio_vapi_fixtures import create_mock_provisioner, generate_available_numbers
    from tests.fixtures.genai_fixtures import create_mock_genai_client, MockGenAIClient
    from tests.fixtures.gcs_fixtures import create_mock_gcs_client, create_mock_faiss_service
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

# Twilio/VAPI fixtures
from tests.fixtures.twilio_vapi_fixtures import (
    MockHTTPResponse,
    TwilioResponseFactory,
    VAPIResponseFactory,
    MockRequestsSession,
    create_mock_provisioner,
    generate_available_numbers,
    generate_twilio_number,
    generate_address,
    AVAILABLE_NUMBERS_ZA,
    AVAILABLE_NUMBERS_US,
    TWILIO_NUMBERS_LIST,
    ADDRESSES_LIST,
)

# GenAI fixtures
from tests.fixtures.genai_fixtures import (
    MockGenAIResponse,
    MockGenAIModel,
    MockGenAIModels,
    MockGenAIClient,
    create_mock_genai_client,
    create_travel_inquiry_response,
    create_quote_ready_response,
    create_clarification_response,
    create_greeting_response,
    TRAVEL_CONSULTANT_RESPONSES,
    FALLBACK_RESPONSE,
)

# GCS and FAISS fixtures
from tests.fixtures.gcs_fixtures import (
    MockGCSBlob,
    MockGCSBucket,
    MockGCSClient,
    MockFAISSIndex,
    MockDocstore,
    MockDocument,
    MockSentenceTransformer,
    create_mock_gcs_client,
    create_mock_faiss_service,
    create_mock_rag_corpus_response,
    generate_mock_embedding,
    generate_mock_search_results,
    generate_mock_documents,
    KNOWLEDGE_BUCKET_CONFIG,
    SAMPLE_SEARCH_RESULTS,
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
    # Twilio/VAPI mocks
    "MockHTTPResponse",
    "TwilioResponseFactory",
    "VAPIResponseFactory",
    "MockRequestsSession",
    "create_mock_provisioner",
    # Twilio/VAPI data generators
    "generate_available_numbers",
    "generate_twilio_number",
    "generate_address",
    # Twilio/VAPI response templates
    "AVAILABLE_NUMBERS_ZA",
    "AVAILABLE_NUMBERS_US",
    "TWILIO_NUMBERS_LIST",
    "ADDRESSES_LIST",
    # GenAI mocks
    "MockGenAIResponse",
    "MockGenAIModel",
    "MockGenAIModels",
    "MockGenAIClient",
    "create_mock_genai_client",
    # GenAI response generators
    "create_travel_inquiry_response",
    "create_quote_ready_response",
    "create_clarification_response",
    "create_greeting_response",
    # GenAI response templates
    "TRAVEL_CONSULTANT_RESPONSES",
    "FALLBACK_RESPONSE",
    # GCS mocks
    "MockGCSBlob",
    "MockGCSBucket",
    "MockGCSClient",
    "create_mock_gcs_client",
    # FAISS mocks
    "MockFAISSIndex",
    "MockDocstore",
    "MockDocument",
    "MockSentenceTransformer",
    "create_mock_faiss_service",
    "create_mock_rag_corpus_response",
    # GCS/FAISS data generators
    "generate_mock_embedding",
    "generate_mock_search_results",
    "generate_mock_documents",
    # GCS/FAISS response templates
    "KNOWLEDGE_BUCKET_CONFIG",
    "SAMPLE_SEARCH_RESULTS",
]
