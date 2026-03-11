"""Shared FastAPI app factory — eliminates duplicated main.py boilerplate."""

import asyncio
import sys
import uuid
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any

import openai
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from shared.config import get_config
from shared.utils import (
    LLMLoggingCallbackHandler,
    ToolLoggingCallbackHandler,
    setup_logging,
    setup_telemetry,
)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


def _extract_reply(raw: Any) -> str:
    """Parse content blocks from Responses API into plain text."""
    if isinstance(raw, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in raw
            if not isinstance(block, dict) or block.get("type") != "reasoning"
        )
    return raw or ""


def create_app(
    title: str,
    create_agent_fn: Callable[..., CompiledStateGraph],
    *,
    include_teams: bool = False,
    module_path: str = "",
    on_startup: Callable[[], Awaitable[None]] | None = None,
) -> FastAPI:
    """Build a FastAPI app for any agent with /health, /chat, and optional /api/messages.

    Args:
        title: Human-readable name for the service (used in logs and OpenAPI docs).
        create_agent_fn: Factory that returns the compiled LangGraph (receives an
            optional ``checkpointer`` keyword argument).
        include_teams: When ``True``, mounts the Teams/Bot Service adapter at
            ``POST /api/messages``.
        module_path: Reserved for future use.
        on_startup: Optional async callable invoked during the lifespan startup phase,
            before the agent is created.  Failures are logged as warnings and do not
            prevent the server from starting.  Intended for one-time initialisation
            tasks such as fetching an access token.
    """

    logger = setup_logging(title.lower().replace(" ", "-"))

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = get_config()
        try:
            setup_telemetry(config.application_insights_connection_string)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to configure telemetry: %s", exc)

        if on_startup is not None:
            try:
                await on_startup()
            except Exception as exc:  # noqa: BLE001
                logger.warning("Startup hook failed: %s", exc)

        redis_url = config.redis_url.strip()
        if not redis_url:
            logger.info("No REDIS_URL configured; starting without persistent LangGraph checkpointing")
            app.state.agent = create_agent_fn(checkpointer=None)
            logger.info("%s ready", title)
            yield
            return

        async with AsyncRedisSaver.from_conn_string(redis_url) as checkpointer:
            await checkpointer.asetup()
            app.state.agent = create_agent_fn(checkpointer=checkpointer)
            logger.info("%s ready", title)
            yield

    app = FastAPI(title=title, lifespan=lifespan)

    if include_teams:
        from shared.teams_adapter import create_teams_router

        app.include_router(create_teams_router(lambda: app.state.agent))

    def get_agent(request: Request) -> CompiledStateGraph:
        return request.app.state.agent

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest, agent: Annotated[CompiledStateGraph, Depends(get_agent)]) -> ChatResponse:
        session_id = req.session_id or str(uuid.uuid4())
        try:
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=req.message)]},
                config={
                    "configurable": {"thread_id": session_id},
                    "callbacks": [ToolLoggingCallbackHandler(logger), LLMLoggingCallbackHandler()],
                },
            )
        except openai.RateLimitError as exc:
            logger.warning("Rate limit hit: %s", exc)
            raise HTTPException(status_code=429, detail="The AI service is currently rate-limited. Please retry in a moment.") from exc
        except openai.APIStatusError as exc:
            logger.error("OpenAI API error %s: %s", exc.status_code, exc)
            raise HTTPException(status_code=502, detail=f"Upstream AI service error: {exc.message}") from exc
        reply = _extract_reply(result["messages"][-1].content)
        return ChatResponse(reply=reply, session_id=session_id)

    return app


def run_app(app_import: str, port: int = 8088) -> None:
    """Run a FastAPI app with uvicorn, handling Windows event loop policy."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = uvicorn.Config(app_import, host="0.0.0.0", port=port, reload=False)
    server = uvicorn.Server(config)
    asyncio.run(server.serve())
