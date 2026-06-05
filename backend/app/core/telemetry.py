"""
OpenTelemetry setup — P1-4.

Initialises distributed tracing with auto-instrumentation for:
  - FastAPI (HTTP spans per request)
  - SQLAlchemy (DB query spans)
  - Redis (cache operation spans)

Exports to an OTLP-compatible collector (Jaeger / Tempo / etc.) when
OTEL_EXPORTER_OTLP_ENDPOINT is set; otherwise falls back to the no-op
exporter so the app starts cleanly without a collector.

All log records are enriched with trace_id + span_id so that logs can
be correlated with traces in Grafana.

Configuration via environment variables (standard OTEL conventions):
  OTEL_SERVICE_NAME         — service name (default: settings.APP_NAME)
  OTEL_EXPORTER_OTLP_ENDPOINT — OTLP gRPC endpoint (e.g. http://jaeger:4317)
  OTEL_TRACES_SAMPLER       — sampler type: "always_on", "parentbased_traceidratio"
  OTEL_TRACES_SAMPLER_ARG   — sample ratio (0.0–1.0) for ratio sampler
"""

import logging
import os
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


def setup_telemetry(app=None) -> None:
    """
    Configure OpenTelemetry TracerProvider and instrument the application.

    Safe to call even when OTEL packages are partially installed — falls back
    gracefully if any component is unavailable.

    Args:
        app: The FastAPI application instance (used for FastAPI instrumentation).
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    except ImportError:
        logger.warning("opentelemetry-sdk not installed — tracing disabled")
        return

    # ── Resource ──────────────────────────────────────────────────────────────
    resource = Resource.create({
        SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", settings.APP_NAME),
        SERVICE_VERSION: settings.APP_VERSION,
        "deployment.environment": settings.ENVIRONMENT,
    })

    # ── Sampler ───────────────────────────────────────────────────────────────
    sampler = _build_sampler()

    # ── Exporter ──────────────────────────────────────────────────────────────
    exporter = _build_exporter()

    # ── TracerProvider ────────────────────────────────────────────────────────
    provider = TracerProvider(resource=resource, sampler=sampler)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # ── Auto-instrumentation ──────────────────────────────────────────────────
    _instrument_fastapi(app)
    _instrument_sqlalchemy()
    _instrument_redis()

    # ── Logging bridge — inject trace_id into every log record ───────────────
    _inject_trace_context_into_logging()

    logger.info(
        "OpenTelemetry initialised",
        extra={
            "service": os.getenv("OTEL_SERVICE_NAME", settings.APP_NAME),
            "exporter": type(exporter).__name__,
        },
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_sampler():
    """Build the appropriate OTEL sampler from env vars."""
    try:
        from opentelemetry.sdk.trace.sampling import (
            ALWAYS_ON,
            ParentBased,
            TraceIdRatioBased,
        )
        sampler_type = os.getenv("OTEL_TRACES_SAMPLER", "parentbased_always_on")
        if sampler_type == "traceidratio":
            ratio = float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "0.1"))
            return TraceIdRatioBased(ratio)
        if sampler_type == "parentbased_traceidratio":
            ratio = float(os.getenv("OTEL_TRACES_SAMPLER_ARG", "0.1"))
            return ParentBased(root=TraceIdRatioBased(ratio))
        return ALWAYS_ON  # default
    except Exception:
        from opentelemetry.sdk.trace.sampling import ALWAYS_ON
        return ALWAYS_ON


def _build_exporter():
    """Build OTLP exporter if endpoint is configured; else console exporter."""
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if otlp_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            logger.info("OTEL: using OTLP gRPC exporter → %s", otlp_endpoint)
            return OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        except ImportError:
            logger.warning("opentelemetry-exporter-otlp not installed; falling back to console exporter")

    # Fallback: console exporter (useful for local dev)
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter
    return ConsoleSpanExporter()


def _instrument_fastapi(app) -> None:
    """Auto-instrument FastAPI for HTTP span creation."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
        else:
            FastAPIInstrumentor().instrument()
        logger.debug("OTEL: FastAPI instrumented")
    except Exception as exc:
        logger.warning("OTEL FastAPI instrumentation failed: %s", exc)


def _instrument_sqlalchemy() -> None:
    """Auto-instrument SQLAlchemy for DB query spans."""
    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument()
        logger.debug("OTEL: SQLAlchemy instrumented")
    except Exception as exc:
        logger.warning("OTEL SQLAlchemy instrumentation failed: %s", exc)


def _instrument_redis() -> None:
    """Auto-instrument Redis for cache operation spans."""
    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        RedisInstrumentor().instrument()
        logger.debug("OTEL: Redis instrumented")
    except Exception as exc:
        logger.warning("OTEL Redis instrumentation failed: %s", exc)


def _inject_trace_context_into_logging() -> None:
    """
    Add a logging.Filter that injects trace_id and span_id into every
    log record, enabling log-trace correlation in Grafana Loki / Tempo.
    """
    try:
        from opentelemetry import trace as otel_trace

        class TraceContextFilter(logging.Filter):
            def filter(self, record: logging.LogRecord) -> bool:
                span = otel_trace.get_current_span()
                ctx = span.get_span_context()
                if ctx and ctx.is_valid:
                    record.trace_id = format(ctx.trace_id, "032x")
                    record.span_id = format(ctx.span_id, "016x")
                else:
                    record.trace_id = "0" * 32
                    record.span_id = "0" * 16
                return True

        # Attach to the root logger so every logger inherits it
        logging.getLogger().addFilter(TraceContextFilter())
        logger.debug("OTEL: trace context injected into logging")
    except Exception as exc:
        logger.warning("OTEL logging bridge setup failed: %s", exc)


def get_tracer(name: str = __name__):
    """Convenience function — returns an OTEL tracer for manual instrumentation."""
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        return _NoopTracer()


class _NoopTracer:
    """Minimal no-op tracer used when opentelemetry is not installed."""

    def start_as_current_span(self, name, **kwargs):
        from contextlib import nullcontext
        return nullcontext()
