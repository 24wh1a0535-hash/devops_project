"""
mcp_server/tools.py
--------------------
Data-access functions used by the MCP server tools.

Each function automatically routes to the correct data source:

    DEMO_MODE=true  → Local CSV files  (no cloud needed)
    DEMO_MODE=false → Databricks Unity Catalog tables

The vector search for policy documents routes through:
    vector_search/search.py → local keyword store  (DEMO_MODE=true)
                             → Databricks Vector Search (DEMO_MODE=false)

These functions are kept separate from the MCP wiring so they can be
unit-tested directly without starting a server.
"""

import csv
import logging
import os
import pathlib
from typing import Optional

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _data_dir() -> pathlib.Path:
    base = pathlib.Path(__file__).parent.parent
    return base / os.getenv("DATA_DIR", "data")


def _read_csv(filename: str) -> list[dict]:
    filepath = _data_dir() / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _is_demo() -> bool:
    return os.getenv("DEMO_MODE", "true").lower() == "true"


# ── Employee data ─────────────────────────────────────────────────────────────

def get_employee_info(
    department: Optional[str] = None,
    employee_id: Optional[str] = None,
    visible_fields: Optional[list[str]] = None,
) -> dict:
    """
    Return employee information filtered by department or employee_id.

    Routes to:
        DEMO_MODE=true  → employees.csv
        DEMO_MODE=false → Databricks Unity Catalog employees table
    """
    # Normalise inputs
    if department is not None:
        if not isinstance(department, str):
            return {"error": "Invalid 'department'. Must be a string."}
        department = department.strip() or None

    if employee_id is not None:
        if not isinstance(employee_id, str):
            return {"error": "Invalid 'employee_id'. Must be a string."}
        employee_id = employee_id.strip().upper() or None

    if _is_demo():
        rows = _get_employees_local(department, employee_id)
        source = "local_csv"
    else:
        rows = _get_employees_databricks(department, employee_id)
        source = "databricks_unity_catalog"

    if isinstance(rows, dict) and "error" in rows:
        return rows

    if visible_fields:
        rows = [{k: v for k, v in row.items() if k in visible_fields} for row in rows]

    return {"employees": rows, "count": len(rows), "source": source}


def _get_employees_local(department, employee_id) -> list[dict]:
    try:
        rows = _read_csv("employees.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}
    if employee_id:
        rows = [r for r in rows if r.get("employee_id", "").upper() == employee_id]
    elif department:
        rows = [r for r in rows if r.get("department", "").lower() == department.lower()]
    return rows


def _get_employees_databricks(department, employee_id) -> list[dict]:
    try:
        from databricks.client import get_connection, get_catalog, get_schema
        from databricks.queries import query_employees
        conn = get_connection()
        return query_employees(conn, get_catalog(), get_schema(), department, employee_id)
    except Exception as e:
        logger.error("Databricks employee query failed: %s. Falling back to local CSV.", e)
        return _get_employees_local(department, employee_id)


# ── Department data ───────────────────────────────────────────────────────────

def get_department_info(department_name: Optional[str] = None) -> dict:
    """
    Return department information.

    Routes to:
        DEMO_MODE=true  → departments.csv
        DEMO_MODE=false → Databricks Unity Catalog departments table
    """
    if department_name is not None:
        if not isinstance(department_name, str):
            return {"error": "Invalid 'department_name'. Must be a string."}
        department_name = department_name.strip() or None

    if _is_demo():
        rows = _get_departments_local(department_name)
        source = "local_csv"
    else:
        rows = _get_departments_databricks(department_name)
        source = "databricks_unity_catalog"

    if isinstance(rows, dict) and "error" in rows:
        return rows

    return {"departments": rows, "count": len(rows), "source": source}


def _get_departments_local(department_name) -> list[dict]:
    try:
        rows = _read_csv("departments.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}
    if department_name:
        rows = [r for r in rows if r.get("department_name", "").lower() == department_name.lower()]
    return rows


def _get_departments_databricks(department_name) -> list[dict]:
    try:
        from databricks.client import get_connection, get_catalog, get_schema
        from databricks.queries import query_departments
        conn = get_connection()
        return query_departments(conn, get_catalog(), get_schema(), department_name)
    except Exception as e:
        logger.error("Databricks department query failed: %s. Falling back to local CSV.", e)
        return _get_departments_local(department_name)


# ── Project data ──────────────────────────────────────────────────────────────

def get_project_info(
    project_id: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """
    Return project information with optional filters.

    Routes to:
        DEMO_MODE=true  → projects.csv
        DEMO_MODE=false → Databricks Unity Catalog projects table
    """
    if project_id is not None:
        project_id = str(project_id).strip().upper() or None
    if department is not None:
        department = str(department).strip() or None
    if status is not None:
        status = str(status).strip() or None

    if _is_demo():
        rows = _get_projects_local(project_id, department, status)
        source = "local_csv"
    else:
        rows = _get_projects_databricks(project_id, department, status)
        source = "databricks_unity_catalog"

    if isinstance(rows, dict) and "error" in rows:
        return rows

    return {"projects": rows, "count": len(rows), "source": source}


def _get_projects_local(project_id, department, status) -> list[dict]:
    try:
        rows = _read_csv("projects.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}
    if project_id:
        rows = [r for r in rows if r.get("project_id", "").upper() == project_id]
    if department:
        rows = [r for r in rows if r.get("department", "").lower() == department.lower()]
    if status:
        rows = [r for r in rows if r.get("status", "").lower() == status.lower()]
    return rows


def _get_projects_databricks(project_id, department, status) -> list[dict]:
    try:
        from databricks.client import get_connection, get_catalog, get_schema
        from databricks.queries import query_projects
        conn = get_connection()
        return query_projects(conn, get_catalog(), get_schema(), project_id, department, status)
    except Exception as e:
        logger.error("Databricks project query failed: %s. Falling back to local CSV.", e)
        return _get_projects_local(project_id, department, status)


# ── Policy / document search ──────────────────────────────────────────────────

def _relevant_excerpt(text: str, query: str, window: int = 600) -> str:
    """
    Return the most relevant portion of a chunk for the given query.

    Finds the first query keyword that appears in the text and returns
    a window of characters centred on that match.  This prevents the
    common case where a keyword (e.g. "password") sits far past the
    first 500 characters of a large chunk that starts with a document
    header, making the plain [:500] excerpt useless.

    Falls back to the first `window` characters when no keyword is found.
    """
    text_lower = text.lower()
    # Try each whitespace-delimited token from the query (longest first so
    # multi-word hits beat single-character noise words).
    keywords = sorted(query.lower().split(), key=len, reverse=True)
    hit_pos = -1
    for kw in keywords:
        pos = text_lower.find(kw)
        if pos != -1:
            hit_pos = pos
            break

    if hit_pos == -1:
        # No keyword found — return the start of the chunk.
        return text[:window]

    # Centre a window around the hit; extend to sentence/word boundaries.
    start = max(0, hit_pos - window // 4)
    end   = min(len(text), start + window)
    # Don't cut in the middle of a word.
    if start > 0:
        start = text.rfind(" ", 0, start) + 1  # step back to word boundary
    excerpt = text[start:end].strip()
    return excerpt


def search_company_policy(query: str, document: Optional[str] = None) -> dict:
    """
    Search company policy documents for relevant content.

    Routes to:
        DEMO_MODE=true  → Local keyword search (vector_search/search.py)
        DEMO_MODE=false → Databricks Vector Search

    This is NOT the old line-by-line grep. It uses the vector_search
    module which performs scored chunk retrieval.

    Args:
        query:    Search keywords or question.
        document: Optional filter: 'company_policy', 'leave_policy',
                  or 'security_policy'.
    """
    if not isinstance(query, str) or not query.strip():
        return {"error": "Invalid 'query'. Must be a non-empty string."}
    query = query.strip()

    valid_docs = {"company_policy", "leave_policy", "security_policy"}
    if document:
        document = document.strip().lower()
        if document not in valid_docs:
            return {
                "error": f"Unknown document '{document}'. "
                         f"Choose from: {sorted(valid_docs)}"
            }

    from vector_search.search import search_documents
    result = search_documents(query=query, doc_filter=document, top_k=5)

    # Re-format results for the MCP tool response.
    # Use _relevant_excerpt() instead of a plain [:500] slice so that keywords
    # buried deep in a large chunk (e.g. "PASSWORD POLICY" at char 1220 of a
    # 400-word security-policy chunk) are actually included in the excerpt the
    # LLM receives.
    formatted = []
    for r in result.get("results", []):
        full_text = r.get("text", "")
        formatted.append({
            "document": r.get("doc_name", ""),
            "excerpt":  _relevant_excerpt(full_text, query),
            "score":    r.get("score", 0),
            "source":   r.get("source", ""),
        })

    mode = result.get("mode", "local_keyword_search")
    # "source" is read by agent/nodes.py to populate the Streamlit Details panel.
    # Without this key the panel shows "unknown".
    if "databricks" in mode:
        source = "databricks_vector_search"
    else:
        source = "local_document"

    return {
        "query":   query,
        "results": formatted,
        "count":   len(formatted),
        "mode":    mode,
        "source":  source,
    }
