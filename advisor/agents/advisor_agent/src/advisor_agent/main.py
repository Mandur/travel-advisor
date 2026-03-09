"""Entrypoint for the routing agent exposed via FastAPI."""

from shared.app_factory import create_app, run_app
from advisor_agent.agent import create_agent

app = create_app("Advisor Agent", create_agent, include_teams=True)

if __name__ == "__main__":
    run_app("advisor_agent.main:app")
