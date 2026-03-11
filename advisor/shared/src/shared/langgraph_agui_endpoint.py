"""
This is a rewrite of ag_ui_langgraph.add_langgraph_fastapi_endpoint:
https://github.com/ag-ui-protocol/ag-ui/blob/bd606a1dcd9ae209e0c6f4382d4a2569a535a368/integrations/langgraph/python/ag_ui_langgraph/endpoint.py#L9

We can't use the original version directly because it expects the agent to be available at the time of endpoint creation,
but in our architecture, the agent is created asynchronously during the FastAPI app's lifespan.
"""

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from ag_ui.core.types import RunAgentInput
from ag_ui.encoder import EventEncoder


def add_langgraph_fastapi_endpoint_patched(
    app: FastAPI, path: str = "/agent/sample_agent_id"
):
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
