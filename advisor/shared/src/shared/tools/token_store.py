"""Token store: fetches and refreshes the Hotelligence bearer token via headless browser."""

from __future__ import annotations

from functools import lru_cache

from shared.config import get_config
from shared.utils import setup_logging

logger = setup_logging("token-store")


class TokenStore:
    """Manages automatic fetching and refreshing of the Hotelligence bearer token.

    On startup, ``initialize()`` is called to fetch a fresh token via the
    headless-browser token fetcher (token_fatcher).  On 401/403 from the API,
    ``refresh()`` is called to obtain a new token and update the HTTP client.

    Falls back to ``HOTELLIGENCE_BEARER_TOKEN`` from config when browser
    credentials are not configured.
    """

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
            logger.info("Hotelligence token refreshed successfully")
        else:
            logger.warning("Could not refresh token — browser credentials not configured")


@lru_cache(maxsize=1)
def get_token_store() -> TokenStore:
    """Return the shared TokenStore singleton."""
    return TokenStore()
