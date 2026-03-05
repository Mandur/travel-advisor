"""Routing agent — supervisor that orchestrates domain agents using agent-as-tool pattern."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from meeting_broker.agent import create_agent as create_meeting_broker_agent
from travel_advisor_agent.agent import create_agent as create_travel_advisor_agent
from shared.config import get_config
from shared.utils import create_llm, setup_logging

if TYPE_CHECKING:
    from langgraph.graph.state import CompiledStateGraph
    from langgraph.checkpoint.base import BaseCheckpointSaver

logger = setup_logging("routing-agent")

SUPERVISOR_INSTRUCTIONS = """You are a helpful assistant for a hospitality platform.
Users ask questions about hotel travel and meeting scheduling.
Use the specialist tools to gather information, then respond directly to the user.

Rules:
- NEVER mention tool names (travel_advisor, meeting_broker)
- NEVER say "I called a tool" or "The specialist said"
- NEVER reveal internal API names, agent names, or system names
- Synthesize information from specialists into one coherent, helpful response
- If a capability failed, describe the gap in user terms
  (e.g., "I wasn't able to retrieve pricing details right now — please try again")
- Be concise and professional"""


def create_agent(checkpointer: "BaseCheckpointSaver") -> "CompiledStateGraph":
    """Create and return the routing supervisor agent as a compiled LangGraph.

    Domain sub-agents are compiled without a checkpointer because each tool
    call is a stateless single-turn invocation.  Only the supervisor graph
    carries the persistent session state via ``checkpointer``.

    Args:
        checkpointer: LangGraph checkpointer for persistent supervisor sessions.
    """
    config = get_config()

    # Build stateless domain graphs (no checkpointer — used as single-turn tools)
    _travel_graph = create_travel_advisor_agent()
    _meeting_graph = create_meeting_broker_agent()

    @tool
    async def travel_advisor(query: str) -> str:
        """Use for questions about hotel pricing, availability, destinations, price forecasts, and travel planning."""
        result = await _travel_graph.ainvoke({"messages": [HumanMessage(content=query)]})
        return result["messages"][-1].content  # type: ignore[index]

    @tool
    async def meeting_broker(query: str) -> str:
        """Use for RFP submissions and inquiries about group meetings and events, including sourcing venue proposals, comparing conference room options, negotiating rates, and coordinating catering, AV equipment, and room setup."""
        result = await _meeting_graph.ainvoke({"messages": [HumanMessage(content=query)]})
        return result["messages"][-1].content  # type: ignore[index]

    supervisor_llm = create_llm(config.gpt5_2_chat_deployment)
    graph = create_react_agent(
        supervisor_llm,
        [travel_advisor, meeting_broker],
        state_modifier=SystemMessage(SUPERVISOR_INSTRUCTIONS),
        checkpointer=checkpointer,
    )

    logger.info("Routing supervisor agent created successfully")
    return graph
