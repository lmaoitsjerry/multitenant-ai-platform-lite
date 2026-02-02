"""
OpenTelemetry Tracing Setup

Opt-in distributed tracing for the Multi-Tenant AI Platform.
Instruments FastAPI and outgoing HTTP requests.

Enable via environment variable:
    ENABLE_TRACING=true

Exports:
    - GCP Cloud Trace in production (when GOOGLE_CLOUD_PROJECT is set)
    - Console/stdout in development

Tracing failures never affect the application -- all setup is wrapped in try/except.
"""

import os
import logging

logger = logging.getLogger(__name__)


def setup_tracing(app=None):
    """
    Initialize OpenTelemetry tracing if ENABLE_TRACING=true.

    Args:
        app: FastAPI application instance (optional, for FastAPI instrumentation).

    Returns:
        True if tracing was successfully initialized, False otherwise.
    """
    if os.getenv("ENABLE_TRACING", "false").lower() != "true":
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor

        service_name = os.getenv("OTEL_SERVICE_NAME", "multitenant-ai-platform")
        environment = os.getenv("ENVIRONMENT", "development")

        resource = Resource.create({
            SERVICE_NAME: service_name,
            "deployment.environment": environment,
        })

        provider = TracerProvider(resource=resource)

        # Choose exporter based on environment
        gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
        if gcp_project and environment in ("production", "prod"):
            try:
                from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
                exporter = CloudTraceSpanExporter(project_id=gcp_project)
                logger.info(f"Tracing: exporting to GCP Cloud Trace (project={gcp_project})")
            except ImportError:
                logger.warning("Tracing: google-cloud-trace-exporter not installed, falling back to console")
                from opentelemetry.sdk.trace.export import ConsoleSpanExporter
                exporter = ConsoleSpanExporter()
        else:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            exporter = ConsoleSpanExporter()
            logger.info("Tracing: exporting to console (development mode)")

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # Instrument FastAPI
        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("Tracing: FastAPI instrumented")

        # Instrument outgoing HTTP requests (requests library)
        RequestsInstrumentor().instrument()
        logger.info("Tracing: outgoing HTTP requests instrumented")

        logger.info("OpenTelemetry tracing initialized successfully")
        return True

    except ImportError as e:
        logger.warning(f"Tracing: OpenTelemetry packages not installed ({e}). Tracing disabled.")
        return False
    except Exception as e:
        logger.error(f"Tracing: failed to initialize ({e}). Tracing disabled.")
        return False
