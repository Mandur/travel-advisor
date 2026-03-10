"""RFP agent definition using LangGraph."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

from langchain.agents import create_agent as _build_agent
from langchain_core.tools import tool

from shared.config import get_config
from shared.utils import create_llm, setup_logging
from meeting_broker.agent import _RFP_TOOLS

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.base import BaseCheckpointSaver

logger = setup_logging("rfp-agent")


def _agent_version() -> str:
    try:
        return version("rfp-agent")
    except PackageNotFoundError:
        return "unknown"

RFP_AGENT_INSTRUCTIONS = """\
You are an RFP Sales Assistant for a hospitality platform.
Use the available tools to search, retrieve, enrich, and update RFPs.

Rules:
- If asked about this agent's version/build/release, call agent_version.
- Always retrieve current data before presenting information -- never guess.
- Share intermediate results with the user as you gather them (e.g. after a search, \
briefly summarize what was found before fetching full details).
- Never write data back without explicit user confirmation.
- Keep responses concise; use structured lists and tables.
- When asked to score an RFP, evaluate: Budget (25%), Strategic Fit (20%), \
Win Probability (20%), Completeness (20%), Urgency (15%)."""


@tool
def agent_version() -> str:
    """Return this agent's version."""
    return f"RFP Agent version {_agent_version()}"


def create_agent(checkpointer: "BaseCheckpointSaver | None" = None) -> "CompiledStateGraph":
    """Create and return the RFP agent as a compiled LangGraph."""
    config = get_config()
    llm = create_llm(config.gpt5_mini_deployment, use_previous_response_id=True)
    graph = _build_agent(
        llm,
        [*_RFP_TOOLS, agent_version],
        system_prompt=RFP_AGENT_INSTRUCTIONS,
        checkpointer=checkpointer,
    )
    logger.info("RFP agent created with %d tools", len(_RFP_TOOLS) + 1)
    return graph
