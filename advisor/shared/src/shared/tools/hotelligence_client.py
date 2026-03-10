"""Async GraphQL client for the Hotelligence360 advisor endpoint."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from shared.config import get_config

_CHATBOT_QUERY = """
query chatbot($property: PropertyInput!, $message: String!) {
  chatbot(property: $property, message: $message) {
    assistance_response
    bubble_prompts
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

    def __init__(self, url: str, bearer_token: str, timeout: float = 60.0) -> None:
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
        tc_prop_id: int,
        owned_prop_id: int,
        message: str,
    ) -> dict[str, Any]:
        """Send a chatbot query to the Hotelligence360 GraphQL endpoint.

        Args:
            tc_prop_id: The TravelClick property ID (integer).
            owned_prop_id: The owned property ID (integer).
            message: Natural language question to ask the advisor.

        Returns:
            Dict with ``assistance_response`` (str) and ``bubble_prompts`` (list).

        Raises:
            httpx.HTTPStatusError: On non-2xx responses.
            RuntimeError: If the GraphQL response contains errors.
        """
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
        resp = await self._client.post(self._url, json=payload)
        resp.raise_for_status()
        body: dict[str, Any] = resp.json()
        if "errors" in body:
            raise RuntimeError(f"GraphQL errors: {body['errors']}")
        return body["data"]["chatbot"]

    async def aclose(self) -> None:
        await self._client.aclose()


@lru_cache(maxsize=1)
def get_hotelligence_client() -> HotelligenceClient:
    """Return a cached singleton HotelligenceClient built from AgentConfig."""
    config = get_config()
    return HotelligenceClient(
        url=config.hotelligence_graphql_url,
        bearer_token=config.hotelligence_bearer_token,
        timeout=config.hotelligence_timeout,
    )
