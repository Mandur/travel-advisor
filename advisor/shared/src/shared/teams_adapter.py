"""Teams adapter factory for the Microsoft 365 Agents SDK.

Creates a FastAPI router exposing POST /api/messages for Azure Bot Service /
Microsoft Teams, bridging M365 activity protocol to a LangGraph CompiledStateGraph.
All M365 SDK imports are isolated here — nothing Teams-specific leaks into
individual agent packages.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from microsoft_agents.hosting.core import TurnContext, TurnState
from microsoft_agents.hosting.core.app import AgentApplication
from microsoft_agents.hosting.core.storage import MemoryStorage
from microsoft_agents.hosting.fastapi import CloudAdapter, start_agent_process
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.activity import load_configuration_from_env

from dotenv import dotenv_values

from shared.config import get_config
from shared.utils import setup_logging, LLMLoggingCallbackHandler, ToolLoggingCallbackHandler
from os import environ

logger = setup_logging("teams-adapter")


# ---------------------------------------------------------------------------
# Microsoft Graph — Teams activity feed notifications
# ---------------------------------------------------------------------------


class NotificationRequest(BaseModel):
    """Request body for POST /notify."""

    user_id: str
    """AAD object ID of the recipient."""
    message: str
    """Free-form notification text shown in the activity feed."""
    topic: str = "Advisor Notification"
    """Display label for the notification topic."""
    web_url: str = "https://teams.microsoft.com"
    """Deep-link URL attached to the notification (must start with teams.microsoft.com)."""


class GraphNotificationClient:
    """Sends Microsoft Teams activity feed notifications via Microsoft Graph.

    Authenticates using ``DefaultAzureCredential`` — resolves to a Managed Identity
    when running in Azure Container Apps, and to ``az login`` / environment variables
    for local development.

    The credential requires the service principal (or MI) to have the
    ``TeamsActivity.Send.User`` **application** permission granted in Entra ID.
    Grant it once with:

    .. code-block:: powershell

        $graph = Get-MgServicePrincipal -Filter "displayName eq 'Microsoft Graph'"
        $role  = $graph.AppRoles | Where-Object { $_.Value -eq 'TeamsActivity.Send.User' }
        New-MgServicePrincipalAppRoleAssignment \\
            -ServicePrincipalId <MI_ObjectId> \\
            -PrincipalId       <MI_ObjectId> \\
            -ResourceId        $graph.Id \\
            -AppRoleId         $role.Id
    """

    _GRAPH_BASE = "https://graph.microsoft.com/v1.0"
    _GRAPH_SCOPE = "https://graph.microsoft.com/.default"

    def __init__(self) -> None:
        from azure.identity import DefaultAzureCredential  # lazy import — not needed by all agents

        self._credential = DefaultAzureCredential()

    def _get_token(self) -> str:
        """Return a fresh bearer token for Microsoft Graph."""
        return self._credential.get_token(self._GRAPH_SCOPE).token

    async def send_activity_notification(
        self,
        user_id: str,
        message: str,
        topic: str = "Advisor Notification",
        web_url: str = "https://teams.microsoft.com",
    ) -> None:
        """POST a ``systemDefault`` activity feed notification to a Teams user.

        Args:
            user_id: AAD object ID of the recipient user.
            message: Free-form text displayed in the Activity feed item
                     (maps to the ``systemDefaultText`` template parameter).
            topic:   Notification topic label shown as the title.
            web_url: Deep-link URL; must start with ``teams.microsoft.com``.

        Raises:
            RuntimeError: If the Graph API returns a non-success status code.
        """
        token = self._get_token()
        url = f"{self._GRAPH_BASE}/users/{user_id}/teamwork/sendActivityNotification"
        payload = {
            "topic": {
                "source": "text",
                "value": topic,
                "webUrl": web_url,
            },
            "activityType": "systemDefault",
            "previewText": {"content": message},
            "templateParameters": [
                {"name": "systemDefaultText", "value": message},
            ],
        }
        config = get_config()
        ssl_verify: bool | str = config.ssl_ca_bundle if config.ssl_ca_bundle else config.ssl_verify
        async with httpx.AsyncClient(verify=ssl_verify) as client:
            resp = await client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
        if resp.status_code not in (202, 204):
            raise RuntimeError(
                f"Graph notification failed [{resp.status_code}]: {resp.text}"
            )
        logger.info("Teams notification sent: user=%s topic=%r", user_id, topic)

    @classmethod
    def from_config(cls) -> "GraphNotificationClient":
        """Convenience factory — reads nothing from config currently but makes
        the call site future-proof if per-environment settings are needed."""
        return cls()


def create_notification_router() -> APIRouter:
    """Create a FastAPI router exposing ``POST /notify``.

    The endpoint accepts a :class:`NotificationRequest` body and sends a
    Microsoft Teams activity feed notification to the specified user via the
    Microsoft Graph API using the ambient Managed Identity credential.

    When ``NOTIFY_API_KEY`` is set in the environment the caller must supply
    the same value in an ``X-Notify-Key`` header, providing a lightweight
    shared-secret guard for internal Container App traffic.
    """
    router = APIRouter()

    @router.post("/notify")
    async def notify(
        req: NotificationRequest,
        x_notify_key: str | None = Header(default=None, alias="X-Notify-Key"),
    ) -> dict:
        config = get_config()
        if config.notify_api_key and x_notify_key != config.notify_api_key:
            raise HTTPException(status_code=401, detail="Invalid or missing X-Notify-Key header")

        graph_client = GraphNotificationClient.from_config()
        try:
            await graph_client.send_activity_notification(
                user_id=req.user_id,
                message=req.message,
                topic=req.topic,
                web_url=req.web_url,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send Teams notification to user=%s: %s", req.user_id, exc)
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return {"status": "sent"}

    return router


def create_teams_router(get_agent: Callable[[], Any]) -> APIRouter:
    """Create a FastAPI router that handles Teams / Bot Service activities.

    Args:
        get_agent: Zero-argument callable that returns the initialised Agent.
                   Called on every incoming activity so it must be fast
                   (typically just ``lambda: app.state.agent``).

    Returns:
        An ``APIRouter`` with a single ``POST /api/messages`` route wired to
        the M365 Agents SDK ``CloudAdapter``.  Include it in any FastAPI app
        with ``app.include_router(create_teams_router(...))``.
    """
    # Merge .env file values with real env vars (real env vars take precedence).
    # This allows local dev to use a .env file without manually exporting every
    # CONNECTIONS__* variable in the shell.
    env = {**dotenv_values(".env"), **dict(environ)}
    agents_sdk_config = load_configuration_from_env(env)

    # Build a connection manager only when SERVICE_CONNECTION is configured
    # (i.e. when running against a real Bot Service / Teams channel).
    # Without it the adapter runs in anonymous mode, which is fine for local
    # dev where you hit /chat directly and never receive a Bot Service JWT.
    connection_manager = None
    if agents_sdk_config.get("CONNECTIONS", {}).get("SERVICE_CONNECTION"):
        connection_manager = MsalConnectionManager(**agents_sdk_config)
        logger.info("Teams adapter: using MsalConnectionManager (SERVICE_CONNECTION configured)")
    else:
        logger.warning(
            "Teams adapter: no SERVICE_CONNECTION configured — "
            "/api/messages runs in anonymous mode (local dev only)"
        )

    adapter = CloudAdapter(connection_manager=connection_manager)  # type: ignore[arg-type]  # SDK accepts None at runtime despite the type hint
    agent_app: AgentApplication[TurnState] = AgentApplication[TurnState](
        storage=MemoryStorage(),
        adapter=adapter,
    )

    @agent_app.activity("message")
    async def on_message(context: TurnContext, state: TurnState) -> None:
        """Forward an incoming Teams message to the agent_framework Agent."""
        user_text = (context.activity.text or "").strip()
        if not user_text:
            return

        # Use Teams conversation ID as the persistent session key so that
        # conversation history is preserved across turns in the same chat.
        session_id = (
            context.activity.conversation.id
            if context.activity.conversation
            else str(uuid.uuid4())
        )

        agent = get_agent()
        result = await agent.ainvoke(
            {"messages": [HumanMessage(content=user_text)]},
            config={
                "configurable": {"thread_id": session_id},
                "callbacks": [ToolLoggingCallbackHandler(logger), LLMLoggingCallbackHandler()],
            },
        )

        raw_content = result["messages"][-1].content
        if isinstance(raw_content, list):
            # Responses API returns content blocks: [{"type": "output_text", "text": "..."}]
            reply_text = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in raw_content
            )
        else:
            reply_text = raw_content or ""
        await context.send_activity(reply_text)
        logger.info(
            "Teams message handled: conversation=%s chars_in=%d chars_out=%d",
            session_id,
            len(user_text),
            len(reply_text),
        )

    router = APIRouter()

    @router.post("/api/messages")
    async def messages(request: Request):
        """Bot Framework / Teams messaging endpoint."""
        return await start_agent_process(request, agent_app, adapter)

    @router.get("/api/messages")
    async def messages_get():
        """Health-check probe used by the Azure Bot Service portal."""
        return {"status": "ok"}

    return router
