# Hack Trial — Multi-Agent Advisor

A supervisor agent routes user requests to domain-specialist sub-agents, built on [LangGraph](https://langchain-ai.github.io/langgraph/) + Azure OpenAI.

## Architecture

```
User -> Advisor Agent (gpt-5.2-chat, supervisor)
         |-- rfp_agent tool        -> RFP Agent (gpt-5-mini)
         |                              \-- meeting_broker tools (RFP API)
         |-- property_planning tool -> Property Planning Agent (gpt-5-mini)
```

The **Advisor Agent** keeps a light conversational context and delegates work to sub-agents via the agent-as-tool pattern. Sub-agents run either **in-process** (default, local dev) or over **HTTP** (docker-compose / production), controlled by env vars.

## Project Layout

```
advisor/
  agents/
    advisor_agent/   # Supervisor — routes to sub-agents (deployable)
    rfp/             # RFP management agent (deployable)
    property_planning/  # Property planning agent (deployable)
  tools/
    meeting_broker/  # RFP API tool functions (library, imported by rfp)
    travel_advisor/  # Hotel pricing tools (library)
  shared/            # Config, models, app factory, utilities
infra/               # Terraform for Azure (ACR, Container Apps, Azure Managed Redis, etc.)
scripts/             # Build & deploy helpers
```

## Quick Start

### Prerequisites

- **Python 3.12+**
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)** — fast Python package manager (replaces pip/venv)

### 1. Install dependencies

```bash
uv sync --all-packages
```

> `uv` creates a `.venv` automatically. No need to activate it — `uv run` handles that.

### 2. Configure environment

```bash
cp .env.example .env
# Fill in Azure OpenAI endpoint, deployment names, credentials, and optionally REDIS_URL
```

### 3. Run locally

```bash
# Start the advisor agent (all sub-agents run in-process by default)
uv run --package advisor-agent python -m advisor_agent.main
# Serves on http://localhost:8088 — POST /chat with {"message": "...", "session_id": "..."}
```

Test with the interactive REPL:

```powershell
.\scripts\chat.ps1
```

### 4. Run with Docker Compose (3 containers, HTTP dispatch)

```bash
docker compose up --build
# advisor-agent :8088, rfp-agent :8089, property-planning-agent :8090
```

## Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI resource URL |
| `AZURE_OPENAI_DEPLOYMENT` | Large model name (supervisor) |
| `AZURE_OPENAI_MINI_DEPLOYMENT` | Small model name (sub-agents) |
| `REDIS_URL` | LangGraph checkpoint store (`rediss://...` for Azure Managed Redis) |
| `RFP_AGENT_URL` | If set, advisor calls RFP agent over HTTP instead of in-process |
| `PROPERTY_PLANNING_AGENT_URL` | Same, for property planning agent |

If `REDIS_URL` is left empty, the agents still start locally but LangGraph checkpoint persistence is disabled.
For local persistence, point `REDIS_URL` to Redis Stack or Azure Managed Redis with `RedisJSON` and `RediSearch` enabled.

## Useful Commands

```bash
uv sync --all-packages          # Install / update all workspace packages
uv run pyright                   # Type-check the codebase
uv run --package advisor-agent python -m advisor_agent.main   # Run advisor
uv run --package rfp-agent python -m rfp.main                 # Run RFP agent standalone
docker compose up --build        # Run all agents as containers
```
