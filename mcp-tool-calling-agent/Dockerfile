# =============================================================================
# Dockerfile — ACME Technologies MCP Tool-Calling Agent
# =============================================================================
#
# Production-style Dockerfile for the Streamlit web application.
#
# Key design decisions:
#   - Lightweight python:3.11-slim base image (no dev tools, smaller attack surface)
#   - Non-root user for security
#   - .env is NOT copied — all secrets are injected at runtime via environment
#   - DEMO_MODE=true is the safe default; override at runtime for Databricks
#   - Data files and documents are bundled in the image (they are not secrets)
#   - Streamlit configured to allow external access (--server.address 0.0.0.0)
#
# Build:
#   docker build -t mcp-agent .
#
# Run (DEMO mode — no API key needed for tests):
#   docker run -p 8501:8501 --env-file .env mcp-agent
#
# Run (explicit env vars):
#   docker run -p 8501:8501 \
#     -e DEMO_MODE=true \
#     -e LLM_PROVIDER=openrouter \
#     -e OPENROUTER_API_KEY=sk-or-v1-... \
#     -e LLM_MODEL=openai/gpt-4o-mini \
#     mcp-agent
# =============================================================================

# ── Base image ────────────────────────────────────────────────────────────────
# python:3.11-slim is the standard lightweight choice:
#   - Based on Debian Bookworm slim (~45 MB compressed)
#   - No unnecessary system packages
#   - Matches project Python version requirement (3.10+)
FROM python:3.11-slim

# ── Labels (metadata) ─────────────────────────────────────────────────────────
LABEL maintainer="ACME Technologies DevOps" \
      project="mcp-tool-calling-agent" \
      description="ACME MCP Tool-Calling AI Agent — Streamlit Web UI" \
      version="1.0"

# ── System dependencies ───────────────────────────────────────────────────────
# curl is needed for the container health check.
# --no-install-recommends keeps the image lean.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ── Create non-root user ──────────────────────────────────────────────────────
# Running as root in a container is a security anti-pattern.
RUN groupadd --gid 1001 appgroup && \
    useradd --uid 1001 --gid appgroup --shell /bin/bash --create-home appuser

# ── Working directory ─────────────────────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────────────────────
# Copy requirements first so Docker can cache this layer.
# The layer is only rebuilt when requirements.txt changes.
COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Copy application source ───────────────────────────────────────────────────
# .dockerignore ensures .env, .venv, __pycache__, .git are NOT copied.
# Data files (CSV) and policy documents ARE copied — they are not secrets.
COPY . .

# ── Fix ownership ─────────────────────────────────────────────────────────────
RUN chown -R appuser:appgroup /app

# ── Switch to non-root user ───────────────────────────────────────────────────
USER appuser

# ── Streamlit configuration ───────────────────────────────────────────────────
# These can also be set in ~/.streamlit/config.toml, but env vars are simpler
# for containerised deployments.
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# ── Application defaults ──────────────────────────────────────────────────────
# DEMO_MODE=true is the safe default — no Databricks credentials needed.
# Override with -e DEMO_MODE=false at runtime for production Databricks use.
ENV DEMO_MODE=true
ENV LLM_PROVIDER=openrouter
ENV LLM_MODEL=openai/gpt-4o-mini
ENV DATA_DIR=data
ENV DOCUMENTS_DIR=documents
ENV LOG_LEVEL=INFO

# ── Port ──────────────────────────────────────────────────────────────────────
EXPOSE 8501

# ── Health check ─────────────────────────────────────────────────────────────
# Docker will mark the container as unhealthy if Streamlit stops responding.
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# ── Entry point ───────────────────────────────────────────────────────────────
# --server.address 0.0.0.0  → accept connections from outside the container
# --server.port 8501         → explicit port
# --server.headless true     → no browser auto-open (irrelevant in container)
# --server.fileWatcherType none → disable file watcher in production
CMD ["streamlit", "run", "streamlit_app.py", \
     "--server.address", "0.0.0.0", \
     "--server.port", "8501", \
     "--server.headless", "true", \
     "--server.fileWatcherType", "none"]
