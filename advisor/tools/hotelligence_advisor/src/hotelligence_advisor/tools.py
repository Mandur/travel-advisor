"""LangChain tools for the Hotelligence360 GraphQL advisor endpoint."""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.tools import tool
from pydantic import Field

from shared.tools.hotelligence_client import get_hotelligence_client
from shared.utils import setup_logging

logger = setup_logging("hotelligence-advisor")


@tool
async def query_hotelligence_advisor(
    message: Annotated[str, Field(description="Natural language question, e.g. 'Occ by Segment next 2 months'")],
    tc_prop_id: Annotated[
        int | None,
        Field(
            default=None,
            description=(
                "TravelClick property ID (integer), e.g. 12917. "
                "Required for the FIRST question in a conversation. "
                "Omit if thread_id is provided."
            ),
        ),
    ] = None,
    owned_prop_id: Annotated[
        int,
        Field(
            default=0,
            description="Owned property ID (integer), e.g. 306393. Used alongside tc_prop_id.",
        ),
    ] = 0,
    thread_id: Annotated[
        str | None,
        Field(
            default=None,
            description=(
                "Thread ID returned by a previous query_hotelligence_advisor call. "
                "Use this for follow-up questions — the API maintains property context "
                "so tc_prop_id / owned_prop_id are NOT needed."
            ),
        ),
    ] = None,
) -> dict[str, Any]:
    """Query the Hotelligence360 advisor for hotel performance insights.

    Use this tool for ANY question about hotel BI analytics: occupancy, revenue,
    segmentation, pace reports, forecasts, competitive set, channel mix, LOS,
    ADR, RevPAR, etc.

    Conversation flow:
    1. FIRST question in a session: provide ``tc_prop_id`` (and ``owned_prop_id``).
    2. FOLLOW-UP questions: use the ``thread_id`` from the previous response so the
       API retains property context — no need to repeat property IDs.

    Returns a dict with:
      - ``answer``: The advisor's text answer.
      - ``data_table``: Structured data rows (list of dicts) — present as a table.
      - ``currency_symbol``: Currency used (e.g. "$").
      - ``applied_filters``: Filters the API applied (date range, segments, etc.).
      - ``bubble_prompts``: Suggested follow-up questions — mention these to the user.
      - ``thread``: Thread ID — ALWAYS pass this to the next query as ``thread_id``.
      - ``extracted_metrics``: Metrics used in this query.
    """
    client = get_hotelligence_client()
    raw = await client.query_chatbot(
        message=message,
        tc_prop_id=tc_prop_id,
        owned_prop_id=owned_prop_id,
        thread_id=thread_id,
    )
    assistant = raw.get("assistant_response") or {}
    result = {
        "answer": assistant.get("answer", ""),
        "data_table": assistant.get("data_table", []),
        "currency_symbol": assistant.get("currency_symbol", ""),
        "applied_filters": raw.get("applied_filters", {}),
        "bubble_prompts": raw.get("bubble_prompts", []),
        "extracted_metrics": raw.get("extracted_metrics", []),
        "thread": raw.get("thread", ""),
    }
    prop_label = f"thread={thread_id}" if thread_id else f"property={tc_prop_id}"
    logger.info(
        "Hotelligence query [%s]: %r -> answer length %d chars",
        prop_label,
        message,
        len(result["answer"]),
    )
    return result


HOTELLIGENCE_TOOLS = [query_hotelligence_advisor]
