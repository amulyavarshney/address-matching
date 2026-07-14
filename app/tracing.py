"""Optional OpenTelemetry setup for FastAPI."""

from __future__ import annotations

import os
from typing import Optional

from loguru import logger


def setup_tracing(app, service_name: str = "address-matching") -> bool:
    """
    Instrument the FastAPI app when OTEL is configured and packages exist.

    Enable by setting OTEL_EXPORTER_OTLP_ENDPOINT (and optional
    OTEL_SERVICE_NAME). Returns True if tracing was enabled.
    """
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.debug("OpenTelemetry disabled (OTEL_EXPORTER_OTLP_ENDPOINT unset)")
        return False

    service = os.getenv("OTEL_SERVICE_NAME", service_name)

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        logger.warning(
            "OpenTelemetry packages missing; install with: "
            "pip install -r requirements-optional.txt"
        )
        return False

    try:
        resource = Resource.create({"service.name": service})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        logger.info(
            "OpenTelemetry tracing enabled service=%s endpoint=%s",
            service,
            endpoint,
        )
        return True
    except Exception as exc:
        logger.warning("Failed to enable OpenTelemetry tracing: %s", exc)
        return False


def get_tracer(name: str = "address-matching"):
    """Return a tracer if OTel is installed; otherwise a no-op shim."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return _NoOpTracer()


class _NoOpSpan:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def set_attribute(self, *args, **kwargs):
        return None


class _NoOpTracer:
    def start_as_current_span(self, name: str, **kwargs):
        return _NoOpSpan()
