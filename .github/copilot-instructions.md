# Copilot Instructions -- hack-trial

## Build & Run

This is a **uv workspace** (Python 3.12+). All dependency and package management uses [uv](https://docs.astral.sh/uv/).

```bash
# Install all workspace dependencies
uv sync --all-packages

# Run a specific agent locally (each serves on http://localhost:8088)
uv run --package advisor-agent python -m advisor_agent.main
uv run --package rfp-agent python -m rfp.main
uv run --package property-planning-agent python -m property_planning.main

# Type-check
uv run pyright

# Build a Docker image (context is always the repo root)
docker build -t advisor-agent -f advisor/agents/advisor_agent/Dockerfile .
```

There is no test suite yet. The interactive REPL at `.\scripts\chat.ps1` can be used for manual testing against a running agent.

## Architecture

Multi-agent system built on LangGraph + Azure OpenAI, deployed to Azure Container Apps via Terraform.

**Agent routing pattern:** A supervisor **Advisor Agent** delegates to domain specialists using the **agent-as-tool** pattern with dual-mode dispatch (in-process or HTTP). The supervisor uses the larger model (`gpt-5.2-chat`); domain agents use the smaller model (`gpt-5-mini`).

```
User -> Advisor Agent (gpt-5.2-chat, supervisor)
         |-- rfp_agent tool        -> RFP Agent (gpt-5-mini)
         |                              |-- meeting_broker tools (RFP API)
         |-- property_planning tool -> Property Planning Agent (gpt-5-mini)
```

**Dual-mode dispatch:** Sub-agents can run in-process (default, for local dev) or via HTTP (for docker-compose / production). Controlled by `RFP_AGENT_URL` and `PROPERTY_PLANNING_AGENT_URL` env vars -- empty = in-process, URL = HTTP POST to /chat.

**Workspace packages** (defined in root `pyproject.toml` under `[tool.uv.workspace]`):

| Package | Path | Role |
|---------|------|------|
| `shared` | `advisor/shared/` | Config, models, app factory, Teams adapter, utilities |
| `advisor-agent` | `advisor/agents/advisor_agent/` | Supervisor -- routes to domain agents |
| `rfp-agent` | `advisor/agents/rfp/` | RFP management agent |
| `property-planning-agent` | `advisor/agents/property_planning/` | Property planning agent |
| `travel-advisor` | `advisor/tools/travel_advisor/` | Hotel pricing & forecasting tools (library) |
| `meeting-broker` | `advisor/tools/meeting_broker/` | RFP API tools (library) |

**Project structure:**

- `advisor/agents/` -- Deployable agent services (each has `main.py`, `Dockerfile`, built by docker-compose)
- `advisor/tools/` -- Importable tool library packages (no `main.py`, no `Dockerfile`, used as dependencies by agents)
- `advisor/shared/` -- Shared config, models, app factory, utilities

## Key Conventions

- **NEVER use `create_react_agent` from `langgraph.prebuilt`.** It is deprecated since LangGraph v1.0. Use `from langchain.agents import create_agent` instead. Key differences: the `prompt` parameter is now `system_prompt` (accepts `str` directly, no need to wrap in `SystemMessage`), and `recursion_limit` is no longer a constructor parameter. Import as `_build_agent` to avoid shadowing the local `create_agent()` function.
- **Agent structure:** Each agent package in `advisor/agents/` follows the same layout: `agent.py` defines the agent (instructions + tools via `create_agent()`), `main.py` uses `shared.app_factory.create_app()` to expose it as a FastAPI app with `/chat` and `/health` endpoints.
- **Tool structure:** Each tool package in `advisor/tools/` contains `agent.py` with `@tool`-decorated async functions. Tools are library packages imported by agents -- they have no `main.py` or `Dockerfile`.
- **Configuration:** All config flows through `shared.config.AgentConfig` (Pydantic Settings), which reads from environment variables and `.env` files. Use `get_config()` to access the cached singleton.
- **Tools:** Agent tools are async Python functions decorated with `@tool` from `langchain_core.tools`. They return `dict` (Pydantic models serialized via `.model_dump()`).
- **HTTP client:** `shared.tools.http_client.ApiClient` is an async httpx client with persistent connection pooling.
- **Teams integration:** The Teams/Bot Service adapter is in `shared.teams_adapter`. Only the advisor agent includes it (`POST /api/messages`). Domain agents do not need it.
- **Telemetry:** OpenTelemetry -> Azure Application Insights via `shared.utils.setup_telemetry()`.
- **Logging:** Use `shared.utils.setup_logging(agent_name)` -- produces structured `timestamp | agent | level | message` format.
- **Docker:** All Dockerfiles use multi-stage builds (uv builder -> slim runtime). Build context is always the repo root, not the agent directory. Only agents (not tools) have Dockerfiles.
- **Infrastructure:** Terraform modules in `infra/` provision ACR, AI Foundry, Container Apps, Key Vault, Bot Service, PostgreSQL, and monitoring. Deploy with `terraform apply`.
