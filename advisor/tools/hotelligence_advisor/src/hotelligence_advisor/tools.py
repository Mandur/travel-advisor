"""LangChain tools for the Hotelligence360 GraphQL advisor endpoint."""

from __future__ import annotations

from typing import Annotated, Any

import httpx
from langchain_core.tools import tool
from pydantic import Field

from shared.tools.hotelligence_client import get_hotelligence_client
from shared.tools.token_store import get_token_store
from shared.utils import setup_logging

logger = setup_logging("hotelligence-advisor")


async def _call_chatbot(
    message: str,
    tc_prop_id: int | None,
    owned_prop_id: int,
    thread_id: str | None,
) -> dict[str, Any]:
    """Execute the chatbot query, refreshing the token once on 401/403.

    Also retries once on ReadTimeout (stale keep-alive connection).
    """
    client = get_hotelligence_client()
    try:
        return await client.query_chatbot(
            message=message,
            tc_prop_id=tc_prop_id,
            owned_prop_id=owned_prop_id,
            thread_id=thread_id,
        )
    except httpx.ReadTimeout:
        logger.warning("Hotelligence ReadTimeout — retrying once with a fresh connection")
        client.reset_connection()
        return await client.query_chatbot(
            message=message,
            tc_prop_id=tc_prop_id,
            owned_prop_id=owned_prop_id,
            thread_id=thread_id,
        )
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code in (401, 403):
            logger.warning(
                "Hotelligence auth error %d — refreshing token and retrying",
                exc.response.status_code,
            )
            await get_token_store().refresh()
            return await client.query_chatbot(
                message=message,
                tc_prop_id=tc_prop_id,
                owned_prop_id=owned_prop_id,
                thread_id=thread_id,
            )
        raise


@tool
async def query_hotelligence_advisor(
    message: Annotated[str, Field(description="Natural language question, e.g. 'Occ by Segment next 2 months'")],
    tc_prop_id: Annotated[
        int | None,
        Field(
            default=None,
            description=(
                "TravelClick property ID (integer), e.g. 12917. "
                "Only provide if explicitly mentioned in the user's message. "
                "When omitted, the value is resolved automatically — do NOT ask the user for it."
            ),
        ),
    ] = None,
    owned_prop_id: Annotated[
        int,
        Field(
            default=0,
            description=(
                "Owned property ID (integer), e.g. 306393. "
                "Only provide if explicitly mentioned in the user's message. "
                "When omitted, the value is resolved automatically — do NOT ask the user for it."
            ),
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
       For known demo users the property IDs are injected automatically — no need
       to ask the user for them.
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
    # Auto-fill property IDs from the token store when the authenticated user
    # has hardcoded defaults and no explicit IDs or thread were provided.
    if thread_id is None and tc_prop_id is None:
        defaults = get_token_store().get_default_props()
        if defaults is not None:
            tc_prop_id, owned_prop_id = defaults
            logger.debug(
                "Auto-injected property defaults from token store: tc_prop_id=%d, owned_prop_id=%d",
                tc_prop_id,
                owned_prop_id,
            )

    raw = await _call_chatbot(
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
