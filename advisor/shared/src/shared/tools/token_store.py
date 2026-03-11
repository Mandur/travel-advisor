"""Token store: fetches and refreshes the Hotelligence bearer token via headless browser."""

from __future__ import annotations

import base64
import json
from functools import lru_cache

from shared.config import get_config
from shared.utils import setup_logging

logger = setup_logging("token-store")

# Maps known user emails to their default Hotelligence property IDs.
# These are injected automatically into queries when the authenticated user
# matches a key here, so the LLM never needs to supply them manually.
_USER_PROPERTY_DEFAULTS: dict[str, tuple[int, int]] = {
    "colyndemo@amadeus.com": (267955, 590225),  # (tc_prop_id, owned_prop_id)
}


def _decode_jwt_email(token: str) -> str | None:
    """Extract the email/username from a JWT payload without verifying the signature.

    Tries the ``email``, ``sub``, and ``username`` claims in that order.
    Returns ``None`` if the token is malformed or no matching claim is found.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        # Add padding so base64 decoding doesn't fail on tokens whose payload
        # length is not a multiple of 4.
        padding = "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.b64decode(parts[1] + padding).decode("utf-8"))
        return payload.get("email") or payload.get("sub") or payload.get("username")
    except Exception:  # noqa: BLE001
        return None


class TokenStore:
    """Manages automatic fetching and refreshing of the Hotelligence bearer token.

    On startup, ``initialize()`` is called to fetch a fresh token via the
    headless-browser token fetcher (token_fatcher).  On 401/403 from the API,
    ``refresh()`` is called to obtain a new token and update the HTTP client.

    Falls back to ``HOTELLIGENCE_BEARER_TOKEN`` from config when browser
    credentials are not configured.

    After a successful token fetch the JWT payload is decoded to identify the
    authenticated user.  If that user appears in :data:`_USER_PROPERTY_DEFAULTS`
    the corresponding ``(tc_prop_id, owned_prop_id)`` pair is returned by
    :meth:`get_default_props` and injected automatically into Hotelligence
    queries so the LLM never needs to supply them manually.
    """

    def __init__(self) -> None:
        self._user_email: str | None = None

    def get_default_props(self) -> tuple[int, int] | None:
        """Return ``(tc_prop_id, owned_prop_id)`` for the current user, or ``None``.

        Returns the hardcoded property pair when the authenticated user's email
        matches a key in :data:`_USER_PROPERTY_DEFAULTS`; ``None`` otherwise.
        """
        if self._user_email and self._user_email in _USER_PROPERTY_DEFAULTS:
            return _USER_PROPERTY_DEFAULTS[self._user_email]
        return None

    async def _fetch(self) -> str | None:
        import asyncio
        import os
        import subprocess

        config = get_config()
        if not all([config.hotelligence_web_ui_url, config.hotelligence_login_email, config.hotelligence_login_password]):
            logger.info("Browser credentials not configured; using HOTELLIGENCE_BEARER_TOKEN from env")
            return None

        logger.info("Fetching Hotelligence token via headless browser...")

        # Run the token fetcher in a child process so pyppeteer's signal handlers
        # are registered in that process's main thread, not in uvicorn's async loop.
        # Use `uv run` to ensure the uv workspace package paths are resolved correctly.
        env = {
            **os.environ,
            "WEB_UI_URL": config.hotelligence_web_ui_url,
            "UI_LOGIN_EMAIL": config.hotelligence_login_email,
            "UI_LOGIN_PASSWORD": config.hotelligence_login_password,
        }
        if config.chrome_executable_path:
            env["CHROME_EXECUTABLE_PATH"] = config.chrome_executable_path

        loop = asyncio.get_event_loop()
        proc = await loop.run_in_executor(
            None,
            lambda: subprocess.run(
                ["uv", "run", "--package", "token-fatcher", "python", "-m", "token_fatcher.token_retriever"],
                capture_output=True,
                text=True,
                env=env,
            ),
        )

        if proc.returncode != 0:
            logger.warning("Token fetcher subprocess failed (rc=%d): %s", proc.returncode, proc.stderr.strip())
            return None

        token = proc.stdout.strip()
        return token or None

    async def initialize(self) -> None:
        """Fetch a fresh token at agent startup and inject it into the HTTP client."""
        token = await self._fetch()
        if token:
            from shared.tools.hotelligence_client import get_hotelligence_client  # noqa: PLC0415
            get_hotelligence_client().update_token(token)
            self._user_email = _decode_jwt_email(token)
            if self._user_email:
                logger.info("Authenticated as %s", self._user_email)
                if self.get_default_props():
                    logger.info(
                        "Default property IDs for %s: tc_prop_id=%d, owned_prop_id=%d",
                        self._user_email,
                        *self.get_default_props(),  # type: ignore[misc]
                    )
            logger.info("Hotelligence token initialised successfully")
        else:
            logger.info("Using static HOTELLIGENCE_BEARER_TOKEN")

    async def refresh(self) -> None:
        """Refresh an expired token (called after 401/403) and update the HTTP client."""
        logger.warning("Refreshing Hotelligence token after auth error...")
        token = await self._fetch()
        if token:
            from shared.tools.hotelligence_client import get_hotelligence_client  # noqa: PLC0415
            get_hotelligence_client().update_token(token)
            self._user_email = _decode_jwt_email(token)
            logger.info("Hotelligence token refreshed successfully")
        else:
            logger.warning("Could not refresh token — browser credentials not configured")


@lru_cache(maxsize=1)
def get_token_store() -> TokenStore:
    """Return the shared TokenStore singleton."""
    return TokenStore()
