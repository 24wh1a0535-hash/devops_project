# Architecture — MCP Tool-Calling AI Agent

## Full System Architecture

```mermaid
flowchart TD
    User([👤 User]) --> UI[Streamlit UI\nstreamlit_app.py]
    UI --> Agent[LangGraph Agent\nagent/graph.py]

    Agent --> LLM[LLM via OpenRouter\nChatOpenAI / ChatAnthropic]
    LLM -->|tool_calls| Agent

    Agent --> MCPC[MCP Client\nmcp_client.py]

    MCPC --> T1[get_employee_info]
    MCPC --> T2[get_department_info]
    MCPC --> T3[get_project_info]
    MCPC --> T4[search_company_policy]
    MCPC --> T5[check_user_permission]

    T1 & T2 & T3 -->|DEMO_MODE=true| CSV[(Local CSV Files\ndata/*.csv)]
    T1 & T2 & T3 -->|DEMO_MODE=false| DB[(Databricks\nUnity Catalog)]

    T4 -->|DEMO_MODE=true| KW[Local Keyword Search\nvector_search/search.py]
    T4 -->|DEMO_MODE=false| VS[Databricks\nVector Search]

    T5 --> Perms[permissions.py\nRole Check]

    DB --> UC[Unity Catalog\ncatalog.schema.table]
    VS --> VSI[Vector Search Index\npolicy_docs_index]
```

## Data Flow for a Question

```mermaid
sequenceDiagram
    participant U as User
    participant S as Streamlit
    participant G as LangGraph
    participant L as LLM
    participant M as MCP Client
    participant T as Tool Functions
    participant D as Data Source

    U->>S: Ask question
    S->>G: invoke(question, user_role)
    G->>L: messages + tools
    L-->>G: AIMessage with tool_calls
    G->>M: call_tool(name, args)
    M->>T: check permission
    T->>D: query (CSV or Databricks)
    D-->>T: raw data
    T-->>M: JSON result
    M-->>G: ToolMessage
    G->>L: messages + tool results
    L-->>G: final answer (no tool_calls)
    G-->>S: final_answer
    S-->>U: display answer + metadata
```

## LangGraph Workflow

```mermaid
stateDiagram-v2
    [*] --> call_llm
    call_llm --> tools : LLM requests tool calls
    call_llm --> [*] : LLM gives direct answer
    tools --> call_llm : Tool results returned
```

## Permission Model

```
Application Level (mcp_server/permissions.py)
├── employee  → can call all 5 tools, sees limited fields
├── manager   → same as employee + sees access_level field
└── admin     → same as manager + all fields

Unity Catalog Level (Databricks, production)
├── employees-group   → SELECT on departments, projects
├── managers-group    → SELECT on employees
└── admin-group       → ALL on all tables

NOTE: Application-level checks control what the AI agent shows.
      Unity Catalog checks control what the database returns.
      Both layers must be configured for true enterprise security.
      Application checks alone are NOT sufficient for production.
```

## Component Map

| File | Purpose |
|---|---|
| `streamlit_app.py` | Web UI |
| `app.py` | CLI interface |
| `mcp_client.py` | MCP tool registry + dispatcher |
| `agent/graph.py` | LangGraph graph builder |
| `agent/state.py` | Shared state schema |
| `agent/nodes.py` | LLM node + tool node |
| `agent/prompts.py` | System prompts |
| `mcp_server/server.py` | MCP server (FastMCP/MCPServer) |
| `mcp_server/tools.py` | Data access functions (CSV + Databricks) |
| `mcp_server/permissions.py` | Role-based access control |
| `databricks/client.py` | Databricks connection management |
| `databricks/queries.py` | Parameterised SQL queries |
| `databricks/setup.sql` | Unity Catalog table setup |
| `vector_search/ingest.py` | Document chunking pipeline |
| `vector_search/search.py` | Keyword / Vector Search retrieval |
| `config.py` | Environment config loader |
