"""Property planning agent definition using LangGraph."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

from langchain.agents import create_agent as _build_agent
from langchain_core.tools import tool

from hotelligence_advisor.tools import HOTELLIGENCE_TOOLS
from shared.config import get_config
from shared.utils import create_llm, setup_logging

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.base import BaseCheckpointSaver

logger = setup_logging("property-planning-agent")


def _agent_version() -> str:
    try:
        return version("property-planning-agent")
    except PackageNotFoundError:
        return "unknown"

PROPERTY_PLANNING_INSTRUCTIONS = """\
You are a hotel analytics agent for a hospitality platform.
You help users with hotel performance data: occupancy, ADR, RevPAR, revenue,
segmentation, pace, LOS, channel mix, competitive set, forecasts, and more.

## Version handling
If asked about this agent's version/build/release, call agent_version.

## When to call query_hotelligence_advisor
Call it on the FIRST step when the user asks ANY hotel analytics question.
Do NOT reply with text first — call the tool immediately.

## Argument rules
- Pass the user's question verbatim as the `message` argument.
- If tc_prop_id and owned_prop_id are present in the message, pass them as integers.
- If they are NOT in the message, omit them entirely — they are resolved automatically
  from the authenticated user's session. NEVER ask the user for property IDs.
- For follow-up questions in the same conversation: pass the `thread` value
  from the previous tool result as `thread_id` and omit tc_prop_id/owned_prop_id.

## After the tool returns
- Present the `answer` text directly — no preamble.
- If `data_table` is non-empty, render it as a readable table.
- Append `bubble_prompts` as "You can also ask: ..." suggestions.
- NEVER ask for property IDs — they are always resolved automatically."""


@tool
def agent_version() -> str:
  """Return this agent's version."""
  return f"Property Planning Agent version {_agent_version()}"


def create_agent(checkpointer: "BaseCheckpointSaver | None" = None) -> "CompiledStateGraph":
    """Create and return the property planning agent as a compiled LangGraph."""
    logger.info("Initializing property planning agent checkpointer_enabled=%s", checkpointer is not None)
    config = get_config()
    logger.info("Using deployment for property planning agent deployment=%s", config.gpt5_mini_deployment)
    llm = create_llm(config.gpt5_mini_deployment)
    graph = _build_agent(
        llm,
        [*HOTELLIGENCE_TOOLS, agent_version],
        system_prompt=PROPERTY_PLANNING_INSTRUCTIONS,
        checkpointer=checkpointer,
    )
    logger.info("Property planning agent created successfully tool_count=%d", 1)
    return graph
