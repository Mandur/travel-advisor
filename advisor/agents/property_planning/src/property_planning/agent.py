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
You are a property planning agent for a hospitality platform.
You help users with venue selection, space planning, and hotel performance analytics.

You have access to the Hotelligence360 advisor — use it to answer questions about
occupancy, revenue, segmentation, forecasts, and pace reports for a specific property.

Rules:
- Always ask for (or infer) the property ID before calling Hotelligence tools.
- Present numbers and trends clearly; avoid raw JSON in your responses.
- If the advisor returns bubble_prompts, offer them as suggested follow-up questions."""


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
