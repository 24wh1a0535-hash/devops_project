# MCP Tool-Calling AI Agent for Secure Company Data Access

> **Complete Project — Half 1 + Half 2**

---

## Problem Statement

Company employees spend significant time hunting for information spread across HR systems, project trackers, and policy documents. This project builds a secure AI assistant that can answer natural-language questions by intelligently routing to the right company data source — enforcing access control at every step.

## Proposed Solution

An AI agent that:
1. Understands questions in plain English
2. Uses the Model Context Protocol (MCP) to call authorized company tools
3. Retrieves data from structured databases (Databricks Unity Catalog) or documents (Vector Search)
4. Enforces role-based permissions before returning data
5. Presents results through a clean web UI

---

## Architecture

```
User
 ↓
Streamlit UI (streamlit_app.py)
 ↓
LangGraph Agent (agent/)
 ↓
MCP Client (mcp_client.py)
 ↓
MCP Tools (mcp_server/tools.py)
 ↓
[DEMO_MODE=true]          [DEMO_MODE=false]
Local CSV files     OR    Databricks Unity Catalog
Local keyword search      Databricks Vector Search
 ↓
Result → LangGraph → Final Answer → Streamlit
```

See `docs/architecture.md` for full Mermaid diagrams.

---

## Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.10+ | Core language |
| LangGraph | Agent workflow graph |
| LangChain | LLM integration + tool binding |
| MCP (Model Context Protocol) | Standard tool-calling protocol |
| OpenRouter / OpenAI / Anthropic | LLM provider |
| Streamlit | Web UI |
| Databricks Unity Catalog | Cloud data source (production) |
| Databricks Vector Search | Semantic document retrieval (production) |
| CSV + keyword search | Local demo data source |
| pytest | Testing |

---

## Folder Structure

```
mcp-tool-calling-agent/
├── streamlit_app.py        ← Web UI (run this for the browser demo)
├── app.py                  ← CLI interface
├── mcp_client.py           ← MCP tool registry + dispatcher
├── config.py               ← Environment config loader
├── requirements.txt
├── .env / .env.example
├── .gitignore
│
├── agent/
│   ├── graph.py            ← LangGraph graph (START→LLM→tools→LLM→END)
│   ├── state.py            ← AgentState TypedDict
│   ├── nodes.py            ← call_llm_node + tool_node
│   └── prompts.py          ← System prompts
│
├── mcp_server/
│   ├── server.py           ← MCP server (5 tools)
│   ├── tools.py            ← Data access (CSV + Databricks routing)
│   └── permissions.py      ← Role-based access control
│
├── databricks/
│   ├── client.py           ← Databricks connection management
│   ├── queries.py          ← Parameterised SQL queries
│   └── setup.sql           ← Unity Catalog table setup script
│
├── vector_search/
│   ├── ingest.py           ← Document chunking pipeline
│   └── search.py           ← Keyword / Vector Search retrieval
│
├── data/
│   ├── employees.csv       ← 15 fictional employees
│   ├── departments.csv     ← 5 departments
│   └── projects.csv        ← 7 projects
│
├── documents/
│   ├── company_policy.txt
│   ├── leave_policy.txt
│   └── security_policy.txt
│
├── docs/
│   ├── architecture.md     ← System diagrams
│   ├── setup.md            ← Detailed setup guide
│   └── project_workflow.md ← Workflow diagrams
│
└── tests/
    ├── test_tools.py       ← Data access tests (24 tests)
    ├── test_permissions.py ← Permission tests (21 tests)
    ├── test_agent.py       ← Agent + MCP client tests (12 tests)
    └── test_half2.py       ← Half 2 integration tests (25 tests)
```

---

## Installation

```cmd
cd mcp-tool-calling-agent
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install streamlit
```

---

## Configuration

```cmd
copy .env.example .env
```

Minimum configuration for demo mode:

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here
LLM_MODEL=openai/gpt-4o-mini
DEMO_MODE=true
```

For Databricks (production):

```env
DEMO_MODE=false
DATABRICKS_HOST=https://adb-xxxx.azuredatabricks.net
DATABRICKS_TOKEN=dapi-your-token
DATABRICKS_WAREHOUSE_ID=your-warehouse-id
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=acme_company
DATABRICKS_VECTOR_SEARCH_ENDPOINT=your-endpoint
```

---

## Running the Application

### Streamlit Web UI (recommended)
```cmd
streamlit run streamlit_app.py
```
Open http://localhost:8501

### CLI
```cmd
python app.py
```

---

## Demo Mode

`DEMO_MODE=true` uses:
- Local CSV files for employee/department/project data
- Local keyword scoring for policy document search

This is a **local demo fallback** — not Databricks. It is clearly labeled as such in tool responses and the UI.

---

## Example Questions

```
Who works in the AI department?
What projects are currently active?
Who works in AI and what projects are they working on?
Who works in Security and what are the security policies?
What is the company leave policy?
What are the password requirements?
How many days of annual leave do I get?
Who manages the Engineering department?
Show me restricted salary information.   ← demonstrates permission denial
Who works in the Nonexistent department? ← demonstrates friendly error
```

---

## Security Approach

| Concern | Implementation |
|---|---|
| No hard-coded secrets | All keys in `.env` (gitignored) |
| Role-based access | `permissions.py` checks role before every tool call |
| Field-level access | `employee` role cannot see `access_level` field |
| Input validation | All tool inputs validated before use |
| No arbitrary SQL | Tools use parameterised queries only |
| No code execution | No `eval()` or `exec()` anywhere |
| Safe error handling | Errors returned as messages, never expose internals |
| Secrets not logged | Log statements never include key values |
| Permission-denied response | Clear message: "You do not have permission..." |

### Two Permission Layers

**Application layer** (`permissions.py`):
- Controls what the AI agent *shows* the user
- Enforces field-level visibility (e.g., `access_level`)
- Prevents calling unauthorized tools
- Useful UX safeguard

**Unity Catalog layer** (Databricks, production):
- Enforces access at the *database level*
- Works regardless of which application queries the data
- Required for true enterprise security
- See `databricks/setup.sql` for example grants

Application checks alone are NOT sufficient for production security. Both layers should be configured.

---

## Testing

```cmd
pytest tests/ -v                      # all tests
pytest tests/test_half2.py -v         # Half 2 tests only
SKIP_LLM_TESTS=false pytest tests/ -v # include LLM integration tests
```

Results: **82 passed, 7 skipped** (skipped = LLM integration, requires API key)

---

## DevOps Setup

### CI/CD Architecture

```
GitHub
   ↓
Jenkins
   ↓
Checkout code
   ↓
Install Python dependencies (isolated venv)
   ↓
Run Tests (pytest — 82 passed, 7 skipped)
   ↓
Docker Build (local image — no Docker Hub push)
   ↓
Docker Container Validation (Streamlit health check)
   ↓
Cleanup (remove temp container + venv)
   ↓
SUCCESS
```

### Docker

The application is fully containerised using a `python:3.11-slim` base image.

```cmd
# Build the image
docker build -t mcp-agent .

# Run in DEMO mode
docker run --rm -p 8501:8501 mcp-agent

# Run with full environment
docker run --rm -p 8501:8501 --env-file .env mcp-agent

# Open browser
# http://localhost:8501
```

Key design decisions:
- Non-root user (`appuser`) inside the container
- `.env` is **never** copied into the image — secrets are injected at runtime
- `DEMO_MODE=true` is the safe default inside the container
- Streamlit listens on `0.0.0.0:8501` to accept connections from outside
- Docker `HEALTHCHECK` monitors `http://localhost:8501/_stcore/health`

### Docker Compose

```cmd
docker compose up --build     # build and start
docker compose up --build -d  # detached (background)
docker compose logs -f         # tail logs
docker compose down            # stop and remove containers
```

The compose file maps `8501:8501` and reads environment from `.env` if
present (`.env` is never baked into the image).

### Jenkins

The `Jenkinsfile` defines a declarative pipeline with these stages:

| Stage | Action |
|---|---|
| Checkout | Clone/update from Git SCM |
| Install Dependencies | `pip install -r requirements.txt` into `.ci-venv` |
| Run Tests | `python -m pytest tests/ -v --tb=short` |
| Build Docker Image | `docker build -t mcp-agent:build-N .` |
| Container Validation | Start temp container, check health endpoint |
| Cleanup (always) | Remove temp container and `.ci-venv` |

Jenkins requirements:
- Python 3.10+ in agent PATH
- Docker CLI + daemon accessible to Jenkins user
- Git plugin, Pipeline plugin

No image is pushed to Docker Hub — this is a local CI/CD pipeline.

### Environment Variables and Secrets

Secrets are **never** committed to the repository. They are:

- Stored in `.env` locally (gitignored and dockerignored)
- Injected via `--env-file .env` or `-e KEY=value` at `docker run` time
- Managed via Jenkins Credential Store in CI

The safe demo configuration (no secrets required):
```env
DEMO_MODE=true
```

For Databricks production mode (OAuth — no PAT/token):
```env
DEMO_MODE=false
DATABRICKS_SERVER_HOSTNAME=your-workspace.azuredatabricks.net
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=acme_company
```

See `docs/devops.md` for the complete DevOps reference.

---

## Limitations

1. **Local vector search is keyword-based**, not semantic. True semantic similarity requires Databricks Vector Search with embeddings.
2. **No conversation memory** across sessions. Each question is independent.
3. **Databricks integration** is fully wired but requires real credentials to test.
4. **Role is manually selected** in the UI. A real system would authenticate users and look up their role from a directory service.

---

## Future Enhancements

- Databricks Vector Search with real embeddings (Half 2 production)
- Conversation memory / multi-turn context
- Real authentication (SSO / Databricks SSO)
- Dynamic role lookup from Unity Catalog
- Streaming responses in Streamlit
- Audit logging of all tool calls
