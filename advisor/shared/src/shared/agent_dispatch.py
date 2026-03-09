"""Dual-mode sub-agent dispatch: in-process or HTTP."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from shared.utils import setup_logging

logger = setup_logging("agent-dispatch")

_SUB_AGENT_TIMEOUT = 120  # seconds


async def invoke_agent_inprocess(
    graph: Any,
    query: str,
    config: RunnableConfig,
) -> str:
    """Call a LangGraph sub-agent graph directly (in-process mode)."""
    result = await asyncio.wait_for(
        graph.ainvoke(
            {"messages": [HumanMessage(content=query)]},
            config=config,
        ),
        timeout=_SUB_AGENT_TIMEOUT,
    )
    raw = result["messages"][-1].content
    if isinstance(raw, list):
        return "".join(
            block.get("text", "") if isinstance(block, dict) else str(block)
            for block in raw
            if not isinstance(block, dict) or block.get("type") != "reasoning"
        )
    return raw or ""


async def invoke_agent_http(
    base_url: str,
    query: str,
    session_id: str,
) -> str:
    """Call a sub-agent via its /chat HTTP endpoint."""
    async with httpx.AsyncClient(timeout=_SUB_AGENT_TIMEOUT) as client:
        resp = await client.post(
            f"{base_url.rstrip('/')}/chat",
            json={"message": query, "session_id": session_id},
        )
        resp.raise_for_status()
        return resp.json()["reply"]
