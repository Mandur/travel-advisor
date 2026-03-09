# syntax=docker/dockerfile:1
# Multi-stage build: uv builder → slim Python runtime

# --- Stage 1: Build with uv ---
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /uvx /bin/

WORKDIR /app

# Copy workspace root files
COPY pyproject.toml uv.lock .python-version ./

# Copy shared library
COPY advisor/shared/ advisor/shared/

# Copy all agents (advisor-agent depends on the other two at the workspace level)
COPY advisor/agents/advisor_agent/ advisor/agents/advisor_agent/
COPY advisor/agents/rfp/ advisor/agents/rfp/
COPY advisor/agents/property_planning/ advisor/agents/property_planning/

# Copy tools (used as library dependencies by the routing agent)
COPY advisor/tools/travel_advisor/ advisor/tools/travel_advisor/
COPY advisor/tools/meeting_broker/ advisor/tools/meeting_broker/

# Install dependencies for this specific agent
RUN uv sync --package advisor-agent --no-dev --frozen

# --- Stage 2: Runtime ---
FROM python:3.12-slim

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/advisor/shared/src /app/advisor/shared/src
COPY --from=builder /app/advisor/agents/advisor_agent/src /app/advisor/agents/advisor_agent/src
COPY --from=builder /app/advisor/tools/travel_advisor/src /app/advisor/tools/travel_advisor/src
COPY --from=builder /app/advisor/tools/meeting_broker/src /app/advisor/tools/meeting_broker/src

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Foundry requires port 8088
EXPOSE 8088

CMD ["python", "-m", "advisor_agent.main"]
