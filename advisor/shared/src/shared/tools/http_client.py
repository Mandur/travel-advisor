"""Generic async HTTP client backed by httpx."""

from __future__ import annotations

from typing import Any

import httpx


class ApiClient:
    """Async wrapper around httpx with persistent connection pooling.

    Args:
        base_url: Base URL of the remote API (trailing slash is stripped).
        bearer_token: Optional bearer token sent in the ``Authorization`` header.
        timeout: Request timeout in seconds (default ``60.0``).
    """

    def __init__(
        self,
        base_url: str,
        bearer_token: str = "",
        timeout: float = 60.0,
    ) -> None:
        self.base_url: str = base_url.rstrip("/")
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if bearer_token:
            headers["Authorization"] = f"Bearer {bearer_token}"
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
        )

    # -- helpers ---------------------------------------------------------------

    @staticmethod
    def _strip_none(params: dict[str, Any] | None) -> dict[str, Any]:
        return {k: v for k, v in (params or {}).items() if v is not None}

    @staticmethod
    def _parse(resp: httpx.Response) -> dict[str, Any]:
        if not resp.content:
            return {}
        return resp.json()

    # -- HTTP verbs ------------------------------------------------------------

    async def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = await self._client.get(path, params=self._strip_none(params))
        resp.raise_for_status()
        return self._parse(resp)

    async def post(self, path: str, json: Any = None) -> dict[str, Any]:
        resp = await self._client.post(path, json=json)
        resp.raise_for_status()
        return self._parse(resp)

    async def put(self, path: str, json: Any = None) -> dict[str, Any]:
        resp = await self._client.put(path, json=json)
        resp.raise_for_status()
        return self._parse(resp)

    async def delete(self, path: str) -> dict[str, Any]:
        resp = await self._client.delete(path)
        resp.raise_for_status()
        return self._parse(resp)

    async def aclose(self) -> None:
        await self._client.aclose()
