"""Entrypoint for the routing agent exposed via FastAPI."""

from shared.app_factory import create_app, run_app
from shared.tools.token_store import get_token_store
from advisor_agent.agent import create_agent

app = create_app(
    "Advisor Agent",
    create_agent,
    include_teams=True,
    on_startup=get_token_store().initialize,
)

if __name__ == "__main__":
    run_app("advisor_agent.main:app")
