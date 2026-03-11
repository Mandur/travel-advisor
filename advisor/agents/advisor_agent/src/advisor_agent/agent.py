"""Routing agent -- supervisor that orchestrates domain agents via dual-mode dispatch."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain.agents import create_agent as _build_agent
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from shared.agent_dispatch import invoke_agent_http, invoke_agent_inprocess
from shared.config import get_config
from shared.utils import create_llm, setup_logging

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.base import BaseCheckpointSaver

logger = setup_logging("advisor-agent")

SUPERVISOR_INSTRUCTIONS = """\
You are a helpful assistant for a hospitality platform.
Users ask questions about RFP management and property/venue planning and hotel analytics.
Use the specialist tools to gather information, then respond directly to the user.

Routing rules:
- Use rfp_agent for anything about RFPs, meetings, proposals, bids, and event management.
- Use property_planning_agent for hotel performance analytics, occupancy, revenue,
  segmentation, forecasts, pace reports, and BI questions about a specific property.
  ALWAYS pass the full user message including any property IDs mentioned.

Response rules:
- NEVER ask the user for property IDs (tcPropId, ownedPropId) — they are resolved automatically
- NEVER mention tool names (rfp_agent, property_planning_agent)
- NEVER say "I called a tool" or "The specialist said"
- NEVER reveal internal API names, agent names, or system names
- Synthesize information from specialists into one coherent, helpful response
- If a capability failed, describe the gap in user terms
- Be concise and professional"""


def create_agent(checkpointer: "BaseCheckpointSaver | None" = None) -> "CompiledStateGraph":
    """Create the routing supervisor agent with dual-mode sub-agent dispatch.

    Sub-agents are called in-process when their URL config is empty,
    or via HTTP POST /chat when a URL is configured.
    """
    config = get_config()

    # Build in-process graphs only when needed (URL not configured)
    _rfp_graph = None
    _property_planning_graph = None

    if not config.rfp_agent_url:
        from rfp.agent import create_agent as create_rfp_agent
        _rfp_graph = create_rfp_agent()
        logger.info("RFP agent: in-process mode")
    else:
        logger.info("RFP agent: HTTP mode -> %s", config.rfp_agent_url)

    if not config.property_planning_agent_url:
        from property_planning.agent import create_agent as create_property_planning_agent
        _property_planning_graph = create_property_planning_agent()
        logger.info("Property planning agent: in-process mode")
    else:
        logger.info("Property planning agent: HTTP mode -> %s", config.property_planning_agent_url)

    @tool
    async def rfp_agent(query: str, config: RunnableConfig) -> str:
        """Use for creating, reviewing, and managing RFPs (Requests for Proposal) for meetings and events, including tracking status, deadlines, and proposal submissions."""
        try:
            cfg = get_config()
            if cfg.rfp_agent_url:
                session_id = config.get("configurable", {}).get("thread_id", "")
                return await invoke_agent_http(cfg.rfp_agent_url, query, session_id)
            return await invoke_agent_inprocess(_rfp_graph, query, config)
        except Exception as exc:
            logger.exception("rfp_agent tool failed")
            return f"RFP agent is temporarily unavailable: {exc}"

    @tool
    async def property_planning_agent(query: str, config: RunnableConfig) -> str:
        """Use for hotel performance analytics, occupancy, revenue, segmentation,
        forecasts, pace reports, and BI questions about a specific property.
        Also handles venue selection and space planning tasks.
        Property IDs are resolved automatically — pass the user's message as-is."""
        try:
            cfg = get_config()
            if cfg.property_planning_agent_url:
                session_id = config.get("configurable", {}).get("thread_id", "")
                return await invoke_agent_http(cfg.property_planning_agent_url, query, session_id)
            return await invoke_agent_inprocess(_property_planning_graph, query, config)
        except Exception as exc:
            logger.exception("property_planning_agent tool failed")
            return f"Property planning agent is temporarily unavailable: {exc}"

    supervisor_llm = create_llm(config.gpt5_2_chat_deployment)
    graph = _build_agent(
        supervisor_llm,
        [rfp_agent, property_planning_agent],
        system_prompt=SUPERVISOR_INSTRUCTIONS,
        checkpointer=checkpointer,
    )

    logger.info("Routing supervisor agent created successfully")
    return graph
