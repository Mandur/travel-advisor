# pyright: reportMissingImports=false
"""Minimal token retriever: login to UI and return ACCESS_TOKEN only."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any


def _default_chrome_executable() -> str | None:
    base = Path(__file__).resolve().parents[2]
    exe_name = "chrome.exe" if os.name == "nt" else "chrome"
    candidate = base / "chrome" / exe_name
    return str(candidate) if candidate.exists() else None


async def _accept_cookies_if_present(page: Any) -> None:
    """Accept cookie banner when it exists; noop otherwise."""
    try:
        await page.waitForSelector("#onetrust-accept-btn-handler", {"timeout": 5000})
        await page.click("#onetrust-accept-btn-handler")
    except Exception:
        pass


async def fetch_access_token(
    web_ui_url: str,
    email: str,
    password: str,
    *,
    headless: bool = True,
    chrome_executable: str | None = None,
) -> str | None:
    """Log in to HOSBI UI and return ACCESS_TOKEN from sessionStorage.

    Args:
        web_ui_url: Login page URL.
        email: User login email.
        password: User login password.
        headless: Whether to run browser in headless mode.
        chrome_executable: Optional path to Chrome/Chromium binary.

    Returns:
        ACCESS_TOKEN string, or None if token is not found.
    """
    if not web_ui_url or not email or not password:
        raise ValueError("web_ui_url, email, and password are required")

    import importlib

    pyppeteer = importlib.import_module("pyppeteer")
    launch = pyppeteer.launch

    launch_kwargs: dict[str, object] = {
        "headless": headless,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",  # avoids crashes when /dev/shm is small (containers)
        ],
    }
    resolved_executable = chrome_executable or _default_chrome_executable()
    if resolved_executable:
        launch_kwargs["executablePath"] = resolved_executable

    browser = await launch(**launch_kwargs)
    try:
        page = await browser.newPage()
        await page.setViewport({"width": 1366, "height": 768})
        await page.goto(web_ui_url, {"waitUntil": "networkidle0"})
        await page.waitForSelector("body")

        await _accept_cookies_if_present(page)
        await page.waitForFunction(
            "document.querySelector('form') && document.querySelector('input[name=j_username]')",
            {"timeout": 15000},
        )

        await page.type("input[name='j_username']", email, {"delay": 20})
        await page.type("input[name='j_password']", password, {"delay": 20})
        await page.click("button[type='submit']")

        await asyncio.sleep(7)
        await _accept_cookies_if_present(page)
        await asyncio.sleep(4)

        return await page.evaluate("() => window.sessionStorage.getItem('ACCESS_TOKEN')")
    finally:
        await browser.close()


async def _run_from_env() -> int:
    """Run token retrieval using environment-provided credentials."""
    web_ui_url = os.getenv("WEB_UI_URL", "").strip()
    email = os.getenv("UI_LOGIN_EMAIL", "").strip()
    password = os.getenv("UI_LOGIN_PASSWORD", "").strip()
    chrome_executable = os.getenv("CHROME_EXECUTABLE_PATH", "").strip() or None

    if not web_ui_url or not email or not password:
        print("Missing WEB_UI_URL, UI_LOGIN_EMAIL, or UI_LOGIN_PASSWORD")
        return 2

    token = await fetch_access_token(
        web_ui_url=web_ui_url,
        email=email,
        password=password,
        chrome_executable=chrome_executable,
    )
    if not token:
        print("Token was not found")
        return 1

    print(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run_from_env()))
