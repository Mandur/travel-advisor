"""RFP agent definition using LangGraph."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

from langchain.agents import create_agent as _build_agent
from langchain_core.tools import tool

from shared.config import get_config
from shared.utils import create_llm, setup_logging
from meeting_broker.agent import _RFP_TOOLS
from hotelligence_advisor.tools import ATI_EVALUATION_TOOLS

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
- When a search/list tool returns multiple results, preserve result cardinality in your response.
- Do not collapse a multi-item result to a single example unless the user explicitly asks for top 1.
- For search results, report returned count and list all items unless the user requests a summary.

RFP Scoring / Evaluation workflow:
When the user asks to score, evaluate, or analyze an RFP, follow these steps in order:

1. Retrieve RFP data — call get_rfp with the ID provided by the user.  If the RFP \
was already fetched earlier in this session you may reuse that data.

2. Extract event dates — from the RFP response look for date fields in this priority order:
   - eventBlocks[*].startDate / endDate
   - guestRoomBlocks[*].startDate / endDate
   - Top-level arrivalDate / departureDate

3. Fetch occupancy data — call get_ati_data_for_evaluation with the extracted \
start_date and end_date (YYYY-MM-DD format).  This provides the property's actual \
occupancy picture over the event period.

4. Produce the scoring analysis — combine the RFP details with the occupancy data \
and score the RFP across all five dimensions:
   - Budget (25%): alignment of the event budget with expected revenue.
   - Strategic Fit (20%): event type, segment, and account alignment.
   - Win Probability (20%): competitiveness and proposal readiness.
   - Completeness (20%): how fully the RFP is filled out.
   - Urgency (15%): deadline proximity and decision timeline.
   For each dimension note how the occupancy data (displacement risk, demand \
   context) influences the score.  Conclude with a weighted total and a \
   recommendation (Accept / Negotiate / Decline)."""


_ALL_TOOLS = _RFP_TOOLS + ATI_EVALUATION_TOOLS


@tool
def agent_version() -> str:
    """Return this agent's version."""
    return f"RFP Agent version {_agent_version()}"


def create_agent(checkpointer: "BaseCheckpointSaver | None" = None) -> "CompiledStateGraph":
    """Create and return the RFP agent as a compiled LangGraph."""
    logger.info("Initializing RFP agent checkpointer_enabled=%s", checkpointer is not None)
    config = get_config()
    logger.info("Using deployment for RFP agent deployment=%s", config.gpt5_mini_deployment)
    llm = create_llm(config.gpt5_mini_deployment, use_previous_response_id=True)
    graph = _build_agent(
        llm,
        [*_ALL_TOOLS, agent_version],
        system_prompt=RFP_AGENT_INSTRUCTIONS,
        checkpointer=checkpointer,
    )
    logger.info(
        "RFP agent created tools=%d (meeting_broker=%d ati_evaluation=%d) previous_response_id=%s",
        len(_ALL_TOOLS),
        len(_RFP_TOOLS),
        len(ATI_EVALUATION_TOOLS),
        True,
    )
    return graph
