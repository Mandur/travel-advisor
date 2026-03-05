# Copilot Instructions — hack-trial

## Build & Run

This is a **uv workspace** (Python 3.12+). All dependency and package management uses [uv](https://docs.astral.sh/uv/).

```bash
# Install all workspace dependencies
uv sync --all-packages

# Run a specific agent locally (each serves on http://localhost:8088)
uv run --package routing-agent python -m advisor_agent.main
uv run --package travel-advisor-agent python -m travel_advisor_agent.main
uv run --package meeting-broker-agent python -m meeting_broker_agent.main

# Type-check
uv run pyright

# Build a Docker image (context is always the repo root)
docker build -t routing-agent -f advisor/agents/advisor_agent/Dockerfile .
```

There is no test suite yet. The interactive REPL at `.\scripts\chat.ps1` can be used for manual testing against a running agent.

## Architecture

Multi-agent system built on [Microsoft Agent Framework](https://github.com/microsoft/agent-framework) (`agent_framework`) deployed to Azure Foundry Agent Service or Azure App Service.

**Agent routing pattern:** A supervisor **Routing Agent** classifies user intent (`travel` / `meeting` / `general`) and delegates to specialist agents using the **agent-as-tool** pattern (`Agent.as_tool()`). The routing agent uses the larger model (`gpt-5.2-chat`); domain agents use the smaller model (`gpt-5-mini`).

```
User → Routing Agent (gpt-5.2-chat)
         ├── travel_advisor tool  → Travel Advisor Agent (gpt-5-mini)
         └── meeting_broker tool  → Meeting Broker Agent (gpt-5-mini)
```

**Workspace packages** (defined in root `pyproject.toml` under `[tool.uv.workspace]`):

| Package | Path | Role |
|---------|------|------|
| `shared` | `advisor/shared/` | Config, Pydantic models, telemetry, Teams adapter |
| `routing-agent` | `advisor/agents/advisor_agent/` | Supervisor — depends on all other agent packages |
| `travel-advisor-agent` | `advisor/agents/travel_advisor_agent/` | Hotel pricing & forecasting tools |
| `meeting-broker-agent` | `advisor/agents/meeting_broker_agent/` | Meeting scheduling & room booking tools |

## Key Conventions

- **Agent structure:** Each agent package follows the same layout: `agent.py` defines the agent (instructions + tools via `create_agent()`), `main.py` exposes it as a FastAPI app with `/chat` and `/health` endpoints.
- **Configuration:** All config flows through `shared.config.AgentConfig` (Pydantic Settings), which reads from environment variables and `.env` files. Use `get_config()` to access the cached singleton.
- **Tools:** Agent tools are plain Python functions decorated with `@tool` from `agent_framework`. They return `dict` (Pydantic models serialized via `.model_dump()`).
- **Data models:** Shared Pydantic models live in `shared.models`. Use these for all structured data exchanged between agents and tools.
- **Teams integration:** The Teams/Bot Service adapter is in `shared.teams_adapter`. Only the routing agent includes it (`POST /api/messages`). Domain agents don't need it.
- **Telemetry:** OpenTelemetry → Azure Application Insights via `shared.utils.setup_telemetry()`, called in each agent's FastAPI lifespan.
- **Logging:** Use `shared.utils.setup_logging(agent_name)` — produces structured `timestamp | agent | level | message` format.
- **Docker:** All Dockerfiles use multi-stage builds (uv builder → slim runtime). Build context is always the repo root, not the agent directory.
- **Infrastructure:** Terraform modules in `infra/` provision ACR, AI Foundry, App Service, Cosmos DB, Key Vault, Bot Service, and monitoring. Deploy with `azd up` or `terraform apply`.
