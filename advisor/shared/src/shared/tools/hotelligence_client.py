"""Async GraphQL client for the Hotelligence360 advisor endpoint."""

from __future__ import annotations

from typing import Any

import httpx

from shared.config import get_config

# First-turn query: property context required
_CHATBOT_QUERY = """
query chatbot($property: PropertyInput!, $message: String!) {
  chatbot(property: $property, message: $message) {
    assistant_response {
      answer
      data_table
      currency_symbol
    }
    thread
    error
    bubble_prompts
    deployment_id
    applied_filters
    extracted_metrics
  }
}
"""

# Follow-up query: continues an existing thread, no property needed
_CHATBOT_THREAD_QUERY = """
query chatbot($thread_id: String!, $message: String!) {
  chatbot(thread_id: $thread_id, message: $message) {
    assistant_response {
      answer
      data_table
      currency_symbol
    }
    thread
    error
    bubble_prompts
    deployment_id
    applied_filters
    extracted_metrics
  }
}
"""


class HotelligenceClient:
    """Async GraphQL client for Hotelligence360.

    Args:
        url: Full GraphQL endpoint URL.
        bearer_token: Bearer token for Authorization header.
        timeout: Request timeout in seconds.
    """

    def __init__(self, url: str, bearer_token: str, timeout: float = 120.0) -> None:
        self._url = url
        config = get_config()
        ssl_verify: bool | str = config.ssl_ca_bundle if config.ssl_ca_bundle else config.ssl_verify
        self._client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=timeout,
            verify=ssl_verify,
        )

    async def query_chatbot(
        self,
        message: str,
        tc_prop_id: int | None = None,
        owned_prop_id: int = 0,
        thread_id: str | None = None,
    ) -> dict[str, Any]:
        """Send a chatbot query to the Hotelligence360 GraphQL endpoint.

        Supports two modes:
        - **New conversation**: provide ``tc_prop_id`` (and optionally ``owned_prop_id``).
        - **Follow-up**: provide ``thread_id`` from a previous response; no property needed.

        Args:
            message: Natural language question to ask the advisor.
            tc_prop_id: TravelClick property ID. Required when starting a new conversation.
            owned_prop_id: Owned property ID (default 0). Used in new conversations.
            thread_id: Thread ID from a previous response. Enables follow-up questions.

        Returns:
            Dict with all chatbot response fields including ``thread`` for continuity.

        Raises:
            ValueError: If neither ``tc_prop_id`` nor ``thread_id`` is provided.
            httpx.HTTPStatusError: On non-2xx responses.
            RuntimeError: If the GraphQL response contains errors.
        """
        if thread_id:
            payload = {
                "query": _CHATBOT_THREAD_QUERY,
                "variables": {"thread_id": thread_id, "message": message},
            }
        elif tc_prop_id is not None:
            payload = {
                "query": _CHATBOT_QUERY,
                "variables": {
                    "property": {
                        "tcPropId": tc_prop_id,
                        "ownedPropId": owned_prop_id,
                    },
                    "message": message,
                },
            }
        else:
            raise ValueError("Either tc_prop_id or thread_id must be provided.")

        resp = await self._client.post(self._url, json=payload)
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()
        if "errors" in body:
            raise RuntimeError(f"GraphQL errors: {body['errors']}")
        chatbot = body["data"]["chatbot"]
        if chatbot.get("error"):
            raise RuntimeError(f"Hotelligence error: {chatbot['error']}")
        return chatbot

    def update_token(self, token: str) -> None:
        """Replace the Authorization header with a refreshed bearer token."""
        self._client.headers["Authorization"] = f"Bearer {token}"

    async def aclose(self) -> None:
        await self._client.aclose()


_hotelligence_client: HotelligenceClient | None = None


def get_hotelligence_client() -> HotelligenceClient:
    """Return the shared HotelligenceClient singleton, creating it on first call.

    Unlike a plain ``@lru_cache`` this module-level variable allows the token
    to be updated in-place via :meth:`HotelligenceClient.update_token` without
    recreating the underlying httpx session.
    """
    global _hotelligence_client
    if _hotelligence_client is None:
        config = get_config()
        _hotelligence_client = HotelligenceClient(
            url=config.hotelligence_graphql_url,
            bearer_token=config.hotelligence_bearer_token,
            timeout=config.hotelligence_timeout,
        )
    return _hotelligence_client
