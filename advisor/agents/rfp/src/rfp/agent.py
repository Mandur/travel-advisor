"""RFP agent definition using LangGraph."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain.agents import create_agent as _build_agent

from shared.config import get_config
from shared.utils import create_llm, setup_logging
from meeting_broker.agent import _RFP_TOOLS

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.base import BaseCheckpointSaver

logger = setup_logging("rfp-agent")

RFP_AGENT_INSTRUCTIONS = """\
You are an RFP Sales Assistant for a hospitality platform.
Use the available tools to search, retrieve, enrich, and update RFPs.

Rules:
- Always retrieve current data before presenting information -- never guess.
- Never write data back without explicit user confirmation.
- Keep responses concise; use structured lists and tables.
- When asked to score an RFP, evaluate: Budget (25%), Strategic Fit (20%), \
Win Probability (20%), Completeness (20%), Urgency (15%)."""


def create_agent(checkpointer: "BaseCheckpointSaver | None" = None) -> "CompiledStateGraph":
    """Create and return the RFP agent as a compiled LangGraph."""
    config = get_config()
    llm = create_llm(config.gpt5_mini_deployment)
    graph = _build_agent(
        llm,
        _RFP_TOOLS,
        system_prompt=RFP_AGENT_INSTRUCTIONS,
        checkpointer=checkpointer,
    )
    logger.info("RFP agent created with %d meeting broker tools", len(_RFP_TOOLS))
    return graph
