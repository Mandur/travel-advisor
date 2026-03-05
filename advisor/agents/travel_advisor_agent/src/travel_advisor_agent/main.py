"""Entrypoint for the travel advisor agent exposed via FastAPI."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel
from agent_framework import Agent, Message

from shared.config import get_config
from shared.utils import setup_logging, setup_telemetry
from travel_advisor_agent.agent import create_agent

logger = setup_logging("travel-advisor-agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = get_config()
    setup_telemetry(config.application_insights_connection_string)
    app.state.agent = create_agent()
    logger.info("Travel advisor agent ready")
    yield


app = FastAPI(title="Travel Advisor Agent", lifespan=lifespan)


def get_agent(request: Request) -> Agent:
    return request.app.state.agent


AgentDep = Annotated[Agent, Depends(get_agent)]


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
    session = agent.create_session(session_id=session_id)
    response = await agent.run(Message(role="user", text=req.message), session=session)
    return ChatResponse(reply=response.text or "", session_id=session_id)


if __name__ == "__main__":
    uvicorn.run("travel_advisor_agent.main:app", host="0.0.0.0", port=8088, reload=False)
