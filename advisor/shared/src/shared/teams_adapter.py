"""Teams adapter factory for the Microsoft 365 Agents SDK.

Creates a FastAPI router exposing POST /api/messages for Azure Bot Service /
Microsoft Teams, bridging M365 activity protocol to a LangGraph CompiledStateGraph.
All M365 SDK imports are isolated here — nothing Teams-specific leaks into
individual agent packages.
"""

from __future__ import annotations

import uuid
from typing import Any, Callable

from fastapi import APIRouter, Request
from langchain_core.messages import HumanMessage
from microsoft_agents.hosting.core import TurnContext, TurnState
from microsoft_agents.hosting.core.app import AgentApplication
from microsoft_agents.hosting.core.storage import MemoryStorage
from microsoft_agents.hosting.fastapi import CloudAdapter, start_agent_process
from microsoft_agents.authentication.msal import MsalConnectionManager
from microsoft_agents.activity import load_configuration_from_env

from dotenv import dotenv_values

from shared.utils import setup_logging, LLMLoggingCallbackHandler, ToolLoggingCallbackHandler
from os import environ

logger = setup_logging("teams-adapter")


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
