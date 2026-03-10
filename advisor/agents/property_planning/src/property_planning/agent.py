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
You are a hotel analytics agent. You answer questions about hotel performance using
the Hotelligence360 advisor tool.

IMPORTANT RULES:
- When the user's message contains a property ID (tcPropId) and owned property ID,
  call query_hotelligence_advisor IMMEDIATELY without asking for clarification.
- Extract tcPropId and ownedPropId from the query — they are always integers.
- Pass the user's question verbatim as the 'message' argument.
- If only one ID is mentioned, use it as tc_prop_id and set owned_prop_id to 0.
- If bubble_prompts are returned, present them as suggested follow-up questions.
- Present the assistance_response directly without adding preamble.
- NEVER ask the user to repeat information already present in the message."""


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
