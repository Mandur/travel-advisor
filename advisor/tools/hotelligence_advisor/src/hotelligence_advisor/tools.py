"""LangChain tools for the Hotelligence360 GraphQL advisor endpoint."""

from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from shared.tools.hotelligence_client import get_hotelligence_client
from shared.utils import setup_logging

logger = setup_logging("hotelligence-advisor")


@tool
async def query_hotelligence_advisor(
    tc_prop_id: int,
    owned_prop_id: int,
    message: str,
) -> dict[str, Any]:
    """Query the Hotelligence360 advisor for hotel performance insights.

    Use this tool for questions about occupancy, revenue, segmentation,
    forecasts, pace reports, and other BI analytics for a specific property.

    Args:
        tc_prop_id: The TravelClick property ID (integer), e.g. 12917.
        owned_prop_id: The owned property ID (integer), e.g. 306393.
        message: Natural language question, e.g. "Occ by Segment next 2 months".

    Returns:
        Dict with:
          - ``assistance_response``: The advisor's answer as a string.
          - ``bubble_prompts``: Suggested follow-up questions (list of strings).
    """
    client = get_hotelligence_client()
    result = await client.query_chatbot(
        tc_prop_id=tc_prop_id,
        owned_prop_id=owned_prop_id,
        message=message,
    )
    logger.info(
        "Hotelligence query for property %s: %r -> %d chars",
        tc_prop_id,
        message,
        len(result.get("assistance_response", "")),
    )
    return result


HOTELLIGENCE_TOOLS = [query_hotelligence_advisor]
