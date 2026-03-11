"""Shared FastAPI app factory — eliminates duplicated main.py boilerplate."""

import asyncio
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Annotated, Any, Callable

import openai
import uvicorn
from copilotkit import LangGraphAGUIAgent
from fastapi import Depends, FastAPI, HTTPException, Request
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from shared.config import AgentConfig, get_config
from shared.utils import (
    LLMLoggingCallbackHandler,
    ToolLoggingCallbackHandler,
    setup_logging,
    setup_telemetry,
)

from .langgraph_agui_endpoint import add_langgraph_fastapi_endpoint_patched


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
    agent_id: str,
    title: str,
    create_agent_fn: Callable[..., CompiledStateGraph],
    *,
    include_teams: bool = False,
    include_agui: bool = False,
    module_path: str = "",
) -> FastAPI:
    """Build a FastAPI app for any agent with /health, /chat, and optional /api/messages and AG-UI endpoints."""

    logger = setup_logging(title.lower().replace(" ", "-"))

    @asynccontextmanager
    async def get_checkpointer(config: AgentConfig):
        # AsyncPostgresSaver uses psycopg directly and does not accept SQLAlchemy-style
        # driver suffixes (e.g. "postgresql+psycopg://"). Strip the suffix if present.
        pg_conn = config.postgres_connection_string.replace(
            "postgresql+psycopg://", "postgresql://", 1
        )
        if pg_conn:
            async with AsyncPostgresSaver.from_conn_string(pg_conn) as saver:
                await saver.setup()
                yield saver
        else:
            logger.warning(
                "No Postgres connection string provided, using in-memory checkpointer for %s",
                title,
            )
            yield InMemorySaver()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        config = get_config()
        try:
            setup_telemetry(config.application_insights_connection_string)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to configure telemetry: %s", exc)

        async with get_checkpointer(config) as checkpointer:
            agent = create_agent_fn(checkpointer=checkpointer)
            app.state.agent = agent
            if include_agui:
                app.state.ag_ui_agent = LangGraphAGUIAgent(
                    name=agent_id,
                    description=title,
                    graph=agent,
                )
            logger.info("%s ready", title)
            yield

    app = FastAPI(title=title, lifespan=lifespan)

    if include_agui:
        add_langgraph_fastapi_endpoint_patched(
            app=app,
            path=f"/agent/{agent_id}",
        )

    if include_teams:
        from shared.teams_adapter import create_teams_router

        app.include_router(create_teams_router(lambda: app.state.agent))

    def get_agent(request: Request) -> CompiledStateGraph:
        return request.app.state.agent

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    @app.post("/chat", response_model=ChatResponse)
    async def chat(
        req: ChatRequest, agent: Annotated[CompiledStateGraph, Depends(get_agent)]
    ) -> ChatResponse:
        session_id = req.session_id or str(uuid.uuid4())
        try:
            result = await agent.ainvoke(
                {"messages": [HumanMessage(content=req.message)]},
                config={
                    "configurable": {"thread_id": session_id},
                    "callbacks": [
                        ToolLoggingCallbackHandler(logger),
                        LLMLoggingCallbackHandler(),
                    ],
                },
            )
        except openai.RateLimitError as exc:
            logger.warning("Rate limit hit: %s", exc)
            raise HTTPException(
                status_code=429,
                detail="The AI service is currently rate-limited. Please retry in a moment.",
            ) from exc
        except openai.APIStatusError as exc:
            logger.error("OpenAI API error %s: %s", exc.status_code, exc)
            raise HTTPException(
                status_code=502, detail=f"Upstream AI service error: {exc.message}"
            ) from exc
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
