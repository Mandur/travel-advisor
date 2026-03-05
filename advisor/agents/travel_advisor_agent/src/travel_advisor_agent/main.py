"""Entrypoint for the travel advisor agent exposed via FastAPI."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, Request
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph.state import CompiledStateGraph
from pydantic import BaseModel

from shared.config import get_config
from shared.utils import setup_logging, setup_telemetry
from travel_advisor_agent.agent import create_agent

logger = setup_logging("travel-advisor-agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    setup_telemetry(config.application_insights_connection_string)
    async with AsyncPostgresSaver.from_conn_string(config.postgres_connection_string) as checkpointer:
        await checkpointer.setup()
        app.state.agent = create_agent(checkpointer=checkpointer)
        logger.info("Travel advisor agent ready")
        yield


app = FastAPI(title="Travel Advisor Agent", lifespan=lifespan)


def get_agent(request: Request) -> CompiledStateGraph:
    return request.app.state.agent


AgentDep = Annotated[CompiledStateGraph, Depends(get_agent)]


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str
    session_id: str


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, agent: AgentDep) -> ChatResponse:
    session_id = req.session_id or str(uuid.uuid4())
    result = await agent.ainvoke(
        {"messages": [HumanMessage(content=req.message)]},
        config={"configurable": {"thread_id": session_id}},
    )
    reply = result["messages"][-1].content or ""
    return ChatResponse(reply=reply, session_id=session_id)


if __name__ == "__main__":
    uvicorn.run("travel_advisor_agent.main:app", host="0.0.0.0", port=8088, reload=False)
