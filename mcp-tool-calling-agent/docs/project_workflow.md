# Project Workflow

## End-to-End Request Flow

```mermaid
flowchart TD
    Q[User Question] --> ST[Streamlit UI]
    ST --> AG[LangGraph Agent]
    AG --> LLM[LLM understands intent]
    LLM --> SEL[Select tool(s)]
    SEL --> PERM[Check permission\nmcp_server/permissions.py]
    PERM -->|Denied| DENY[Return permission-denied message]
    PERM -->|Granted| MCP[MCP Client dispatches tool]
    MCP --> ROUTE{DEMO_MODE?}
    ROUTE -->|true| LOCAL[Local CSV / Keyword Search]
    ROUTE -->|false| CLOUD[Databricks UC / Vector Search]
    LOCAL & CLOUD --> RESULT[Tool result JSON]
    RESULT --> LLM2[LLM processes results]
    LLM2 --> ANS[Final answer]
    ANS --> ST2[Streamlit displays answer + metadata]
```

## Multi-Tool Workflow Example

Question: *"Who works in AI and what projects are they on?"*

```
Step 1: LLM identifies need for two tools
Step 2: Call get_employee_info(department="AI")
        → Returns 4 employees with project_ids
Step 3: Call get_project_info(department="AI")
        → Returns 2 active projects
Step 4: LLM combines both results
Step 5: Returns formatted answer with names + project descriptions
```

## Combined Structured + Document Workflow

Question: *"Who works in Security and what are the security policies?"*

```
Step 1: LLM identifies structured + document need
Step 2: Call get_employee_info(department="Security")
        → Returns Security team members
Step 3: Call search_company_policy(query="security policies",
                                   document="security_policy")
        → Returns relevant policy chunks via vector search
Step 4: LLM combines employee list + policy excerpts
Step 5: Returns unified answer
```

## Permission Check Flow

```
User role: employee
Requested tool: get_employee_info
  → can_use_tool("employee", "get_employee_info") → True
  → visible_fields for employee → excludes access_level
  → Tool executes, returns filtered fields

User role: employee
Requested tool: fake_admin_tool
  → can_use_tool("employee", "fake_admin_tool") → False
  → Returns: "You do not have permission to access this information."
```

## Vector Search Document Retrieval

```
Query: "maternity leave"
  ↓
chunk_text() splits policy docs into ~400-word chunks
  ↓
_score_chunk() scores each chunk by keyword frequency
  ↓
Top 5 chunks returned sorted by score
  ↓
search_company_policy() formats and returns excerpts
  ↓
LLM synthesises a natural-language answer
```
