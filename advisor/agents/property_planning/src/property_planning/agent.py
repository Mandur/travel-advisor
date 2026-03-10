"""Property planning agent definition using LangGraph."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain.agents import create_agent as _build_agent

from hotelligence_advisor.tools import HOTELLIGENCE_TOOLS
from shared.config import get_config
from shared.utils import create_llm, setup_logging

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.base import BaseCheckpointSaver

logger = setup_logging("property-planning-agent")

PROPERTY_PLANNING_INSTRUCTIONS = """\
You are a hotel analytics agent for a hospitality platform.
You help users with hotel performance data: occupancy, ADR, RevPAR, revenue,
segmentation, pace, LOS, channel mix, competitive set, forecasts, and more.

## When to call query_hotelligence_advisor
Call it on the FIRST step when the user asks ANY hotel analytics question.
Do NOT reply with text first — call the tool immediately.

## Argument rules
- Extract tc_prop_id and owned_prop_id from the message (integers).
- If only one property ID is present, use it as tc_prop_id and set owned_prop_id=0.
- Pass the user's question verbatim as the `message` argument.
- For follow-up questions in the same conversation: pass the `thread` value
  from the previous tool result as `thread_id` and omit tc_prop_id/owned_prop_id.

## After the tool returns
- Present the `answer` text directly — no preamble.
- If `data_table` is non-empty, render it as a readable table.
- Append `bubble_prompts` as "You can also ask: ..." suggestions.
- NEVER ask for information already present in the user's message.
- Only ask for the tc_prop_id if the question has absolutely no property reference
  and there is no active thread_id."""


def create_agent(checkpointer: "BaseCheckpointSaver | None" = None) -> "CompiledStateGraph":
    """Create and return the property planning agent as a compiled LangGraph."""
    config = get_config()
    llm = create_llm(config.gpt5_mini_deployment)
    graph = _build_agent(
        llm,
        HOTELLIGENCE_TOOLS,
        system_prompt=PROPERTY_PLANNING_INSTRUCTIONS,
        checkpointer=checkpointer,
    )
    logger.info("Property planning agent created successfully")
    return graph
