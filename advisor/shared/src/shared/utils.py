"""Common utility functions for Foundry agents."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel


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


def create_llm(deployment: str) -> "AzureAIChatCompletionsModel":
    """Create an Azure AI Foundry chat model for the given deployment name.

    Uses the ``azure_ai_project_endpoint`` already in ``AgentConfig`` so no
    additional endpoint configuration is required.  Authentication is handled
    by ``DefaultAzureCredential``.
    """
    from azure.identity import DefaultAzureCredential
    from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel

    from shared.config import get_config

    config = get_config()
    return AzureAIChatCompletionsModel(
        endpoint=config.azure_ai_project_endpoint,
        model_name=deployment,  # type: ignore[call-arg]
        credential=DefaultAzureCredential(),
        api_version=config.azure_openai_api_version,
    )
