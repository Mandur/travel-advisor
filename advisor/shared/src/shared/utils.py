"""Common utility functions for Foundry agents."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler

if TYPE_CHECKING:
    from langchain_openai import AzureChatOpenAI


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


class ToolLoggingCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that logs tool calls, results, and errors.

    Pass an instance in the ``callbacks`` key of the LangGraph ``config`` dict
    when calling ``agent.ainvoke()`` to get structured call-level logs from
    every tool invoked during a run.

    Usage::

        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config={
                "configurable": {"thread_id": session_id},
                "callbacks": [ToolLoggingCallbackHandler(logger)],
            },
        )
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        # Maps run_id → tool name so on_tool_end can emit the name without
        # relying on kwargs that aren't guaranteed across LangChain versions.
        self._tool_names: dict[UUID, str] = {}

    # Run callbacks synchronously in the calling thread so log output appears
    # immediately in the agent process stdout (avoids thread-pool dispatch which
    # can swallow log lines in async LangGraph runs).
    run_inline: bool = True

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        name = serialized.get("name", "unknown")
        self._tool_names[run_id] = name
        self._logger.info("Tool call → %s | input: %s", name, input_str[:500])

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        name = self._tool_names.pop(run_id, "unknown")
        output_str = str(output)
        truncated = output_str[:200] + "…" if len(output_str) > 200 else output_str
        self._logger.info("Tool done ← %s | output: %s", name, truncated)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        name = self._tool_names.pop(run_id, "unknown")
        self._logger.error("Tool error ← %s | %s", name, error)


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


def create_llm(deployment: str) -> "AzureChatOpenAI":
    """Create an Azure OpenAI chat model using the Responses API.

    Uses ``azure_openai_endpoint`` from ``AgentConfig`` (env: ``AZURE_OPENAI_ENDPOINT``).
    Authentication is handled by ``DefaultAzureCredential`` via a bearer-token provider.
    """
    from azure.identity import DefaultAzureCredential
    from azure.identity import get_bearer_token_provider
    from langchain_openai import AzureChatOpenAI

    from shared.config import get_config

    config = get_config()
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    return AzureChatOpenAI(
        azure_endpoint=config.azure_openai_endpoint,
        azure_deployment=deployment,
        api_version=config.azure_openai_api_version,
        azure_ad_token_provider=token_provider,
        use_responses_api=True,
    )
