"""Entrypoint for the RFP agent exposed via FastAPI."""

from shared.app_factory import create_app, run_app
from rfp.agent import create_agent

app = create_app("RFP Agent", create_agent)

if __name__ == "__main__":
    run_app("rfp.main:app")
