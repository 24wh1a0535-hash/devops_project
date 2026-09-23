# Setup Guide

## Prerequisites

- Python 3.10 or higher
- An OpenRouter API key (or OpenAI / Anthropic key)
- (Optional for cloud features) Databricks workspace with Unity Catalog enabled

---

## 1. Install Dependencies

```cmd
cd mcp-tool-calling-agent
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install streamlit            # if not already installed
```

---

## 2. Configure Environment

```cmd
copy .env.example .env
```

Open `.env` and fill in:

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-your-key-here
LLM_MODEL=openai/gpt-4o-mini
DEMO_MODE=true
```

---

## 3. Run in Demo Mode (no Databricks needed)

### Streamlit UI
```cmd
streamlit run streamlit_app.py
```
Open http://localhost:8501 in your browser.

### CLI
```cmd
python app.py
```

---

## 4. Run Tests

```cmd
pytest tests/ -v
```

To also run LLM integration tests (requires API key):
```cmd
set SKIP_LLM_TESTS=false
pytest tests/ -v
```

---

## 5. Databricks Setup (production)

### Step 1 — Add credentials to .env
```env
DEMO_MODE=false
DATABRICKS_SERVER_HOSTNAME=your-workspace.azuredatabricks.net
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/your-warehouse-id
DATABRICKS_CATALOG=main
DATABRICKS_SCHEMA=acme_company
DATABRICKS_VECTOR_SEARCH_ENDPOINT=your-vs-endpoint
```

Authentication uses Databricks OAuth (`auth_type="databricks-oauth"`).
No PAT / DATABRICKS_TOKEN is required or supported.

### Step 2 — Create Unity Catalog tables
Run `databricks/setup.sql` in your Databricks SQL editor.
Replace `your_catalog` with your actual catalog name.

### Step 3 — Install Databricks packages
```cmd
pip install databricks-sql-connector databricks-vectorsearch
```

### Step 4 — Create Vector Search index
In the Databricks UI:
1. Create a Delta table with columns: `doc_name`, `chunk_id`, `text`, `source`
2. Create a Vector Search endpoint
3. Create a Vector Search index named `{catalog}.{schema}.policy_docs_index`

### Step 5 — Run the agent
```cmd
streamlit run streamlit_app.py
```

---

## Unity Catalog Permission Setup

Run these grants in Databricks after creating the tables:

```sql
-- Allow all employees to read departments and projects
GRANT SELECT ON TABLE main.acme_company.departments TO `employees-group`;
GRANT SELECT ON TABLE main.acme_company.projects    TO `employees-group`;

-- Allow managers to read employees table
GRANT SELECT ON TABLE main.acme_company.employees   TO `managers-group`;

-- Allow admins full access
GRANT ALL ON SCHEMA main.acme_company TO `admin-group`;
```

**Important:** Unity Catalog grants enforce access at the database level.
The application-level role checks in `permissions.py` are an additional
UI-layer safeguard — they do not replace Unity Catalog security.
