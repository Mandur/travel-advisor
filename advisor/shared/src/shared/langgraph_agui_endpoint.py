"""
Rewrite of ag_ui_langgraph.add_langgraph_fastapi_endpoint because the agent
isn't available at import time of scaffolding the FastAPI app in app_factory.py.

This version allows passing a lambda that returns the agent, enabling dynamic retrieval from app.state.
"""

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder


def add_langgraph_fastapi_endpoint_patched(app: FastAPI, path: str = "/"):
    """Adds endpoints to the FastAPI app to enable AG-UI integration."""

    @app.post(path)
    async def langgraph_agent_endpoint(input_data: RunAgentInput, request: Request):
        # Get the accept header from the request
        accept_header = request.headers.get("accept")

        # Create an event encoder to properly format SSE events
        encoder = EventEncoder(
            accept=accept_header  # pyright: ignore[reportArgumentType]
        )

        async def event_generator():
            agent = app.state.ag_ui_agent
            async for event in agent.run(input_data):
                yield encoder.encode(event)

        return StreamingResponse(
            event_generator(), media_type=encoder.get_content_type()
        )

    @app.get(f"{path}/health")
    def health():
        """Health check."""

        agent = app.state.ag_ui_agent
        return {
            "status": "ok",
            "agent": {
                "name": agent.name,
            },
        }
