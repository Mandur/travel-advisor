"""Common utility functions for Foundry agents."""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
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


class LLMLoggingCallbackHandler(BaseCallbackHandler):
    """LangChain callback handler that serializes every LLM request and response to a JSONL log file.

    Each turn appends two lines to the log file:
    - A ``"request"`` record written when the model is called, containing the
      full message list, model name, and invocation parameters.
    - A ``"response"`` record written when the model returns, containing the
      generated text/message and any ``llm_output`` metadata (token usage, etc.).
    - An ``"error"`` record is written instead of a response when the call fails.

    Usage::

        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=message)]},
            config={
                "configurable": {"thread_id": session_id},
                "callbacks": [
                    ToolLoggingCallbackHandler(logger),
                    LLMLoggingCallbackHandler(),
                ],
            },
        )

    The log file defaults to ``logs/llm_calls.jsonl`` relative to the process
    working directory and is created automatically if it does not exist.
    Set ``log_file`` to an absolute path to control the location.
    """

    # Run synchronously in the calling thread so records are flushed immediately.
    run_inline: bool = True

    def __init__(self, log_file: str | Path = "logs/llm_calls.jsonl") -> None:
        self._log_path = Path(log_file)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)
        # Maps run_id → request record so the response can reference the same run.
        self._pending: dict[UUID, dict[str, Any]] = {}
        # Maps run_id → tool name so on_tool_end/error can emit the name.
        self._tool_names: dict[UUID, str] = {}

    # ── helpers ──────────────────────────────────────────────────────────────

    def _write(self, record: dict[str, Any]) -> None:
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    @staticmethod
    def _serialize_message(msg: Any) -> dict[str, Any]:
        """Convert a LangChain BaseMessage (or any object) to a plain dict."""
        d: dict[str, Any] = {
            "type": getattr(msg, "type", type(msg).__name__),
            "content": getattr(msg, "content", str(msg)),
        }
        # Tool-call requests embedded in assistant messages
        if tool_calls := getattr(msg, "tool_calls", None):
            d["tool_calls"] = tool_calls
        # Tool result messages carry the originating call id
        if tool_call_id := getattr(msg, "tool_call_id", None):
            d["tool_call_id"] = tool_call_id
        # Named messages (e.g. function results) carry a name
        if name := getattr(msg, "name", None):
            d["name"] = name
        return d

    # ── LangChain callbacks ──────────────────────────────────────────────────

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[Any]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when a chat model is about to be invoked."""
        invocation_params = kwargs.get("invocation_params", {})
        # Strip any credential values that may appear in invocation_params.
        safe_params = {
            k: v
            for k, v in invocation_params.items()
            if k not in ("azure_ad_token", "api_key", "azure_ad_token_provider")
        }
        serialized_messages = [
            [self._serialize_message(m) for m in batch]
            for batch in messages
        ]
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": str(run_id),
            "stage": "request",
            "model": serialized.get("name") or (serialized.get("id") or ["unknown"])[-1],
            "invocation_params": safe_params,
            "messages": serialized_messages,
        }
        self._pending[run_id] = {"messages": serialized_messages}
        self._write(record)

    def on_llm_end(
        self,
        response: Any,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when the LLM returns a response."""
        pending = self._pending.pop(run_id, {})
        generations: list[list[dict[str, Any]]] = []
        for batch in getattr(response, "generations", []):
            batch_out: list[dict[str, Any]] = []
            for gen in batch:
                # ChatGeneration wraps a BaseMessage; plain Generation has .text
                if hasattr(gen, "message"):
                    batch_out.append({"message": self._serialize_message(gen.message)})
                else:
                    batch_out.append({"text": getattr(gen, "text", str(gen))})
            generations.append(batch_out)
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": str(run_id),
            "stage": "response",
            "input_messages": pending.get("messages", []),
            "llm_output": getattr(response, "llm_output", {}),
            "generations": generations,
        }
        self._write(record)

    def on_llm_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        """Called when the LLM raises an error."""
        pending = self._pending.pop(run_id, {})
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": str(run_id),
            "stage": "error",
            "input_messages": pending.get("messages", []),
            "error_type": type(error).__name__,
            "error": str(error),
        }
        self._write(record)

    # ── Tool callbacks (written to the same JSONL file) ──────────────────────

    def on_tool_start(
        self,
        serialized: dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when a tool is about to be invoked."""
        name = serialized.get("name", "unknown")
        self._tool_names[run_id] = name
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": str(run_id),
            "parent_run_id": str(parent_run_id) if parent_run_id else None,
            "stage": "tool_start",
            "tool": name,
            "input": input_str,
        }
        self._write(record)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when a tool returns a result."""
        name = self._tool_names.pop(run_id, "unknown")
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": str(run_id),
            "parent_run_id": str(parent_run_id) if parent_run_id else None,
            "stage": "tool_end",
            "tool": name,
            "output": str(output),
        }
        self._write(record)

    def on_tool_error(
        self,
        error: BaseException,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Called when a tool raises an error."""
        name = self._tool_names.pop(run_id, "unknown")
        record: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": str(run_id),
            "parent_run_id": str(parent_run_id) if parent_run_id else None,
            "stage": "tool_error",
            "tool": name,
            "error_type": type(error).__name__,
            "error": str(error),
        }
        self._write(record)


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


def create_llm(deployment: str, use_previous_response_id: bool = False) -> "AzureChatOpenAI":
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
        timeout=None,
        max_retries=2,
        use_previous_response_id=use_previous_response_id,
    )
