"""Property planning agent definition using LangGraph."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain.agents import create_agent as _build_agent
from langchain_core.tools import tool

from shared.config import get_config
from shared.utils import create_llm, setup_logging

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.base import BaseCheckpointSaver

logger = setup_logging("property-planning-agent")

PROPERTY_PLANNING_INSTRUCTIONS = """\
You are a property planning agent for a hospitality platform.
You help users with venue selection, space planning, and property management tasks.

Use the available tools to handle property planning requests."""


@tool
def placeholder_tool(query: str) -> str:
    """Placeholder tool -- replace with actual property planning tools.

    Args:
        query: The user query to process.

    Returns:
        A placeholder response.
    """
    return f"Property planning agent received: {query}"


def create_agent(checkpointer: "BaseCheckpointSaver | None" = None) -> "CompiledStateGraph":
    """Create and return the property planning agent as a compiled LangGraph."""
    config = get_config()
    llm = create_llm(config.gpt5_mini_deployment)
    graph = _build_agent(
        llm,
        [placeholder_tool],
        system_prompt=PROPERTY_PLANNING_INSTRUCTIONS,
        checkpointer=checkpointer,
    )
    logger.info("Property planning agent created successfully")
    return graph
