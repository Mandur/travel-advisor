"""Common utility functions for Foundry agents."""

from __future__ import annotations

import logging
import sys


def setup_logging(agent_name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up structured logging for an agent."""
    logger = logging.getLogger(agent_name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        formatter = logging.Formatter(
            f"%(asctime)s | {agent_name} | %(levelname)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


def setup_telemetry(connection_string: str) -> None:
    """Configure OpenTelemetry export to Azure Application Insights."""
    if not connection_string:
        return

    from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    exporter = AzureMonitorTraceExporter(connection_string=connection_string)
    provider = TracerProvider()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
