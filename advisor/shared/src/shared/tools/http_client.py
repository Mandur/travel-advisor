"""Generic synchronous HTTP client backed by httpx."""

from __future__ import annotations

from typing import Any

import httpx


class ApiClient:
    """Thin synchronous wrapper around httpx.

    Parameters are explicit so the client is not tied to any specific API or
    config key.  Callers are responsible for reading their own config and
    passing the values in.

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
        self._bearer_token: str = bearer_token
        self._timeout: float = timeout

    # ── helpers ──────────────────────────────────────────────────────────────

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if self._bearer_token:
            h["Authorization"] = f"Bearer {self._bearer_token}"
        return h

    @staticmethod
    def _strip_none(params: dict[str, Any] | None) -> dict[str, Any]:
        return {k: v for k, v in (params or {}).items() if v is not None}

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    def _parse(self, resp: httpx.Response) -> dict[str, Any]:
        if not resp.content:
            return {}
        return resp.json()

    # ── HTTP verbs ───────────────────────────────────────────────────────────

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.get(
                self._url(path),
                headers=self._headers(),
                params=self._strip_none(params),
            )
            resp.raise_for_status()
            return self._parse(resp)

    def post(self, path: str, json: Any = None) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.post(self._url(path), headers=self._headers(), json=json)
            resp.raise_for_status()
            return self._parse(resp)

    def put(self, path: str, json: Any = None) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.put(self._url(path), headers=self._headers(), json=json)
            resp.raise_for_status()
            return self._parse(resp)

    def delete(self, path: str) -> dict[str, Any]:
        with httpx.Client(timeout=self._timeout) as client:
            resp = client.delete(self._url(path), headers=self._headers())
            resp.raise_for_status()
            return self._parse(resp)
