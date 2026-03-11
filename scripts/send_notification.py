"""Send a Microsoft Teams activity feed notification via the advisor agent endpoint.

Usage (against a locally running agent):

    uv run --package shared python scripts/send_notification.py \\
        --user-id "569363e2-4e49-4661-87f2-16f245c5d66a" \\
        --message "A new RFP proposal requires your review."

Usage (against the deployed Container App):

    uv run --package shared python scripts/send_notification.py \\
        --url https://<advisor-containerapp-fqdn> \\
        --api-key $env:NOTIFY_API_KEY \\
        --user-id "569363e2-4e49-4661-87f2-16f245c5d66a" \\
        --message "A new RFP proposal requires your review."

Prerequisites:
  • The advisor agent must be running and reachable at --url.
  • The managed identity (or local az login identity) must have the
    ``TeamsActivity.Send.User`` application permission granted in Entra ID.
  • The target user must have the Teams app installed personally.
  • Replace <MICROSOFT_APP_ID> in manifest.json with the managed identity
    client ID before sideloading the updated Teams app package.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

import httpx
from dotenv import load_dotenv


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a Teams activity feed notification via the advisor /notify endpoint.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8088",
        help="Base URL of the advisor agent (default: http://localhost:8088).",
    )
    parser.add_argument(
        "--user-id",
        required=True,
        metavar="AAD_OBJECT_ID",
        help="AAD object ID of the Teams user to notify.",
    )
    parser.add_argument(
        "--message",
        required=True,
        help="Free-form notification text displayed in the Teams Activity feed.",
    )
    parser.add_argument(
        "--topic",
        default="Advisor Notification",
        help="Notification topic label (default: 'Advisor Notification').",
    )
    parser.add_argument(
        "--web-url",
        default="https://teams.microsoft.com",
        help="Deep-link URL attached to the notification (default: https://teams.microsoft.com).",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Value for the X-Notify-Key header (required when NOTIFY_API_KEY is set on the agent).",
    )
    return parser.parse_args()


async def main() -> int:
    load_dotenv()
    args = _parse_args()

    endpoint = args.url.rstrip("/") + "/notify"
    payload = {
        "user_id": args.user_id,
        "message": args.message,
        "topic": args.topic,
        "web_url": args.web_url,
    }
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if args.api_key:
        headers["X-Notify-Key"] = args.api_key

    print(f"Sending notification to {endpoint}")
    print(f"  user_id : {args.user_id}")
    print(f"  topic   : {args.topic}")
    print(f"  message : {args.message}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.post(endpoint, json=payload, headers=headers)
        except httpx.ConnectError as exc:
            print(f"\nERROR: Could not connect to {endpoint}: {exc}", file=sys.stderr)
            print("Is the advisor agent running?", file=sys.stderr)
            return 1

    if resp.status_code == 200:
        print("\nNotification sent successfully.")
        return 0
    else:
        print(f"\nERROR: Agent returned {resp.status_code}: {resp.text}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
