# DevOps Guide — MCP Tool-Calling Agent

## Overview

This document describes the complete DevOps setup for the ACME Technologies
MCP Tool-Calling Agent, including Docker, Docker Compose, Jenkins CI/CD,
environment variables, secrets handling, and testing strategy.

---

## 1. Why Docker?

| Problem | Docker Solution |
|---|---|
| "Works on my machine" | Image bundles exact Python version and dependencies |
| Dependency conflicts | Isolated container environment |
| Deployment consistency | Same image runs on dev, CI, and any server |
| Clean startup | No venv activation, no system Python conflicts |
| Port management | Explicit port mapping (8501:8501) |

The container runs as a non-root user (`appuser`) and never includes secrets —
credentials are injected at runtime as environment variables.

---

## 2. Why Jenkins?

Jenkins provides automated CI/CD that runs on every code push:

- Checks out the code from Git
- Installs Python dependencies into an isolated virtualenv
- Runs the full pytest suite (82 tests, 7 skipped)
- Builds the Docker image
- Starts a temporary container and verifies Streamlit is healthy
- Cleans up all temporary resources

This ensures that broken code can never be deployed — the pipeline fails
before the image is tagged as usable.

---

## 3. CI/CD Workflow

```
Developer pushes to GitHub
         ↓
Jenkins detects change (webhook or poll)
         ↓
Stage 1: Checkout
  → git clone / workspace update
         ↓
Stage 2: Install Dependencies
  → python -m venv .ci-venv
  → pip install -r requirements.txt
         ↓
Stage 3: Run Tests
  → python -m pytest tests/ -v --tb=short
  → 82 passed, 7 skipped (LLM tests skipped without API key)
  → FAIL here = pipeline aborts, no Docker build
         ↓
Stage 4: Build Docker Image
  → docker build -t mcp-agent:build-N .
  → Image built locally — NOT pushed to Docker Hub
         ↓
Stage 5: Docker Container Validation
  → docker run -d --name mcp-agent-ci-N -p 8502:8501 mcp-agent:build-N
  → Wait for Streamlit health endpoint: http://localhost:8502/_stcore/health
  → HTTP 200 = healthy
  → FAIL here = pipeline fails, container logs collected
         ↓
Stage 6: Cleanup (always runs)
  → docker stop mcp-agent-ci-N
  → docker rm mcp-agent-ci-N
  → rm -rf .ci-venv
         ↓
SUCCESS — image is available locally as mcp-agent:latest
```

---

## 4. Environment Variables

### Minimum required (DEMO_MODE)

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here
LLM_MODEL=openai/gpt-4o-mini
DEMO_MODE=true
```

### Full variable reference

| Variable | Default | Description |
|---|---|---|
| `DEMO_MODE` | `true` | `true` = local CSV data; `false` = Databricks |
| `LLM_PROVIDER` | `openrouter` | `openrouter`, `openai`, or `anthropic` |
| `LLM_MODEL` | `openai/gpt-4o-mini` | Model name for the chosen provider |
| `OPENROUTER_API_KEY` | — | OpenRouter API key (secret) |
| `OPENAI_API_KEY` | — | OpenAI API key (secret, if using OpenAI) |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (secret, if using Anthropic) |
| `DATA_DIR` | `data` | Path to CSV data files |
| `DOCUMENTS_DIR` | `documents` | Path to policy documents |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DATABRICKS_SERVER_HOSTNAME` | — | Databricks workspace hostname (production) |
| `DATABRICKS_HTTP_PATH` | — | SQL warehouse HTTP path (production) |
| `DATABRICKS_CATALOG` | `main` | Unity Catalog catalog name |
| `DATABRICKS_SCHEMA` | `acme_company` | Schema inside the catalog |

---

## 5. Secrets Handling

### Rules

1. **Never hardcode secrets** in Dockerfile, docker-compose.yml, Jenkinsfile,
   README, or any committed file.
2. **`.env` is gitignored** and dockerignored — it never enters the image.
3. **Docker image defaults** are safe: `DEMO_MODE=true`, no API key required.
4. **Runtime injection**: secrets are passed with `--env-file .env` or
   `-e VAR=value` at `docker run` time.
5. **Jenkins credentials** are stored in Jenkins Credential Store (not in
   Jenkinsfile). Inject using `withCredentials` block if LLM tests are needed.

### What is safe to commit

| File | Safe? | Reason |
|---|---|---|
| `Dockerfile` | ✅ | No secrets; uses ENV placeholders |
| `docker-compose.yml` | ✅ | Uses `${VAR:-default}` syntax; no real values |
| `Jenkinsfile` | ✅ | References env vars only; no hardcoded secrets |
| `.env.example` | ✅ | Placeholder values only |
| `.env` | ❌ | Contains real API keys — gitignored |

### Databricks authentication

The project uses **Databricks OAuth** (`auth_type="databricks-oauth"`).
No token / PAT is used or required. Configure with:

```env
DATABRICKS_SERVER_HOSTNAME=your-workspace.azuredatabricks.net
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
```

---

## 6. Testing

```bash
# Local (activate venv first on Windows)
.venv\Scripts\activate
python -m pytest tests/ -v --tb=short

# In CI (Jenkinsfile uses a fresh .ci-venv)
python -m pytest tests/ -v --tb=short

# Include LLM integration tests (requires API key)
set SKIP_LLM_TESTS=false
python -m pytest tests/ -v --tb=short
```

**Current result:** 82 passed, 7 skipped

The 7 skipped tests are LLM integration tests that call a live LLM API.
They are skipped by default (`SKIP_LLM_TESTS=true`) so CI passes without
an API key.

---

## 7. Docker Image Build

```bash
# Build the image
docker build -t mcp-agent .

# View layers / size
docker images mcp-agent

# Run in DEMO mode (no API key needed for the UI to start)
docker run --rm -p 8501:8501 -e DEMO_MODE=true mcp-agent

# Run with full configuration from .env
docker run --rm -p 8501:8501 --env-file .env mcp-agent

# Open in browser
# http://localhost:8501
```

### Image structure

| Layer | Content |
|---|---|
| `python:3.11-slim` | Base OS + Python |
| `apt-get install curl` | Health check utility |
| `pip install -r requirements.txt` | All Python dependencies |
| `COPY . .` | Application code, CSV data, policy documents |
| Non-root user | `appuser` (uid 1001) |

**Not included in image:** `.env`, `.venv`, `__pycache__`, `.git`, `.pytest_cache`

---

## 8. Docker Container Validation

The health check endpoint is:

```
http://localhost:8501/_stcore/health
```

This endpoint is built into Streamlit and returns HTTP 200 when the server
is ready. It is used by:

- Docker `HEALTHCHECK` directive in the Dockerfile
- Docker Compose `healthcheck` section
- Jenkins Stage 5 validation loop

```bash
# Manual check (PowerShell)
Invoke-WebRequest -Uri http://localhost:8501/_stcore/health -UseBasicParsing

# Manual check (curl)
curl -f http://localhost:8501/_stcore/health
```

---

## 9. Jenkins Pipeline

### Prerequisites

The Jenkins agent/node must have:

- Python 3.10+ in `PATH` (as `python` or `python3`)
- Docker CLI + Docker daemon accessible (the Jenkins user must be in the
  `docker` group on Linux, or Docker Desktop must be running on Windows)
- Git

### Setup steps

1. Install Jenkins (https://www.jenkins.io/download/)
2. Install plugins: **Git**, **Pipeline**, **Docker Pipeline**
3. Create a new Pipeline job
4. Set SCM to your GitHub repository
5. Set "Script Path" to `Jenkinsfile`
6. (Optional) Add `OPENROUTER_API_KEY` as a Secret Text credential if you
   want LLM integration tests to run in CI
7. Trigger a build

### Pipeline stages summary

| Stage | What it does | Fails pipeline if... |
|---|---|---|
| Checkout | Clones/updates workspace from SCM | Git error |
| Install Dependencies | Creates `.ci-venv`, installs requirements | pip install fails |
| Run Tests | Runs `pytest tests/` | Any test fails |
| Build Docker Image | `docker build -t mcp-agent:build-N .` | Docker build error |
| Container Validation | Starts container, checks health endpoint | Health check fails |
| Cleanup (post) | Stops container, removes venv | Always runs |

### Windows-specific note

On Windows, the Jenkinsfile uses `sh` steps (bash). This requires either:

- Jenkins running on a Linux/WSL agent, or
- Windows Jenkins with Git Bash / WSL in PATH

If Jenkins is running natively on Windows without bash, replace `sh` steps
with `bat` steps and adjust virtualenv activation to `.ci-venv\Scripts\activate`.

---

## 10. Local Development

```bash
# Clone and set up
git clone <repo-url>
cd mcp-tool-calling-agent

# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your API key

# Run the app
streamlit run streamlit_app.py
# Open http://localhost:8501

# Run tests
python -m pytest tests/ -v --tb=short
```

---

## 11. Databricks Production Configuration

When `DEMO_MODE=false`, the agent connects to Databricks using OAuth:

```env
DEMO_MODE=false
DATABRICKS_SERVER_HOSTNAME=your-workspace.azuredatabricks.net
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=acme_company
```

**Authentication:** `auth_type="databricks-oauth"` — no PAT / token required.

### Unity Catalog permission setup

```sql
-- Allow all employees to read departments and projects
GRANT SELECT ON TABLE main.acme_company.departments TO `employees-group`;
GRANT SELECT ON TABLE main.acme_company.projects    TO `employees-group`;

-- Allow managers to read employees table
GRANT SELECT ON TABLE main.acme_company.employees   TO `managers-group`;

-- Allow admins full access
GRANT ALL ON SCHEMA main.acme_company TO `admin-group`;
```

Both the application-level permission checks (`mcp_server/permissions.py`)
and the Unity Catalog grants must be configured for true enterprise security.
Application checks alone are not sufficient for production.

---

## 12. Docker Compose Quick Reference

```bash
# Start (build if needed, run in foreground)
docker compose up --build

# Start in background
docker compose up --build -d

# Check status
docker compose ps

# Tail logs
docker compose logs -f

# Stop and remove containers
docker compose down

# Stop, remove containers AND volumes
docker compose down -v
```

The compose file maps host port 8501 → container port 8501.
Open http://localhost:8501 once the container is healthy.

---

## 13. Troubleshooting

| Issue | Likely cause | Fix |
|---|---|---|
| `docker: command not found` | Docker not installed or not in PATH | Install Docker Desktop; restart terminal |
| Health check fails in Jenkins | Port 8502 in use | Change `TEST_HOST_PORT` in Jenkinsfile |
| `ModuleNotFoundError` in container | Package missing from requirements.txt | Add package to requirements.txt, rebuild |
| `DEMO_MODE=false` connection error | Missing Databricks env vars | Set `DATABRICKS_SERVER_HOSTNAME` and `DATABRICKS_HTTP_PATH` |
| LLM tests skipped | `SKIP_LLM_TESTS=true` (default) | Set `SKIP_LLM_TESTS=false` and provide API key |
| Streamlit not reachable | Wrong address binding | Ensure `--server.address 0.0.0.0` in CMD |
