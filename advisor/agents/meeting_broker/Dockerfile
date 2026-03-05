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

# Copy this agent
COPY advisor/agents/meeting_broker_agent/ advisor/agents/meeting_broker_agent/

# Install dependencies for this specific agent
RUN uv sync --package meeting-broker-agent --no-dev --frozen

# --- Stage 2: Runtime ---
FROM python:3.12-slim

WORKDIR /app

# Copy the virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY --from=builder /app/advisor/shared/src /app/advisor/shared/src
COPY --from=builder /app/advisor/agents/meeting_broker_agent/src /app/advisor/agents/meeting_broker_agent/src

# Add venv to PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Foundry requires port 8088
EXPOSE 8088

CMD ["python", "-m", "meeting_broker_agent.main"]
