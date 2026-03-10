"""Entrypoint for the property planning agent exposed via FastAPI."""

from shared.app_factory import create_app, run_app
from property_planning.agent import create_agent

app = create_app(
    agent_id="property_planning_agent",
    title="Property Planning Agent",
    create_agent_fn=create_agent,
)


if __name__ == "__main__":
    run_app("property_planning.main:app")
