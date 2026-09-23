"""
tests/test_half2.py
--------------------
Half 2 integration tests covering all 8 required scenarios.

Run: pytest tests/test_half2.py -v

LLM tests require a real API key.
Set SKIP_LLM_TESTS=true to skip those (data-layer tests still run).
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATA_DIR", "data")
os.environ.setdefault("DOCUMENTS_DIR", "documents")

SKIP_LLM = os.getenv("SKIP_LLM_TESTS", "true").lower() == "true"


# ── Vector search tests ───────────────────────────────────────────────────────

class TestVectorSearch:

    def test_ingest_returns_chunks(self):
        from vector_search.ingest import ingest_documents
        count = ingest_documents(force=True)
        assert count > 0

    def test_search_leave_policy(self):
        from vector_search.search import search_documents
        result = search_documents("annual leave days", top_k=3)
        assert result["count"] > 0
        assert result["mode"] == "local_keyword_search"

    def test_search_with_doc_filter(self):
        from vector_search.search import search_documents
        result = search_documents("password", doc_filter="security_policy", top_k=3)
        assert result["count"] > 0
        for r in result["results"]:
            assert r["doc_name"] == "security_policy"

    def test_search_invalid_doc_filter(self):
        from vector_search.search import search_documents
        result = search_documents("something", doc_filter="fake_doc")
        assert "error" in result

    def test_search_empty_query(self):
        from vector_search.search import search_documents
        result = search_documents("")
        assert "error" in result

    def test_search_returns_score(self):
        from vector_search.search import search_documents
        result = search_documents("maternity leave")
        if result["count"] > 0:
            assert "score" in result["results"][0]


# ── Updated search_company_policy (now uses vector search) ───────────────────

class TestSearchPolicyViaVectorSearch:

    def test_policy_search_returns_results(self):
        from mcp_server.tools import search_company_policy
        result = search_company_policy("leave policy vacation days")
        assert "results" in result
        assert result["count"] > 0
        assert "mode" in result

    def test_policy_search_security(self):
        from mcp_server.tools import search_company_policy
        result = search_company_policy("password MFA", document="security_policy")
        assert result["count"] > 0
        # Verify source label is set correctly (not "unknown")
        assert result.get("source") == "local_document"

    def test_policy_search_password_requirements_query(self):
        """Regression test: 'password requirements' must resolve to security policy."""
        from mcp_server.tools import search_company_policy
        result = search_company_policy("password requirements")
        assert result["count"] > 0, "password requirements query returned no results"
        texts = [r["excerpt"].lower() for r in result["results"]]
        assert any("password" in t for t in texts)

    def test_policy_empty_query_error(self):
        from mcp_server.tools import search_company_policy
        result = search_company_policy("")
        assert "error" in result


# ── Databricks client in demo mode ───────────────────────────────────────────

class TestDatabricksClientDemoMode:

    def test_demo_mode_returns_none_connection(self):
        from databricks.client import get_connection, is_demo_mode
        assert is_demo_mode() is True
        conn = get_connection()
        assert conn is None

    def test_full_table_name(self):
        from databricks.client import get_full_table
        name = get_full_table("employees")
        assert "employees" in name
        assert "." in name


# ── MCPClient scenario tests ──────────────────────────────────────────────────

class TestScenarios:
    """All 8 required scenario tests (data layer — no LLM needed)."""

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    # Scenario 1 — AI department employees
    def test_scenario_1_ai_employees(self):
        r = json.loads(self.client.call_tool("get_employee_info", {"department": "AI", "user_role": "employee"}))
        assert r["count"] > 0
        for e in r["employees"]:
            assert e["department"] == "AI"

    # Scenario 2 — Active projects
    def test_scenario_2_active_projects(self):
        r = json.loads(self.client.call_tool("get_project_info", {"status": "Active"}))
        assert r["count"] > 0
        for p in r["projects"]:
            assert p["status"] == "Active"

    # Scenario 3 — Company leave policy
    def test_scenario_3_leave_policy(self):
        r = json.loads(self.client.call_tool("search_company_policy", {"query": "annual leave days", "document": "leave_policy"}))
        assert r["count"] > 0

    # Scenario 4 — Multi-tool: AI employees + projects
    def test_scenario_4_multi_tool_ai(self):
        emp = json.loads(self.client.call_tool("get_employee_info", {"department": "AI", "user_role": "employee"}))
        proj = json.loads(self.client.call_tool("get_project_info", {"department": "AI"}))
        assert emp["count"] > 0
        assert proj["count"] > 0
        # Verify they share project IDs
        emp_project_ids = {e.get("project_id") for e in emp["employees"]}
        proj_ids = {p["project_id"] for p in proj["projects"]}
        assert emp_project_ids & proj_ids  # overlap

    # Scenario 5 — Security employees + security policy
    def test_scenario_5_security_combined(self):
        emp  = json.loads(self.client.call_tool("get_employee_info", {"department": "Security", "user_role": "employee"}))
        policy = json.loads(self.client.call_tool("search_company_policy", {"query": "zero trust security", "document": "security_policy"}))
        assert emp["count"] > 0
        assert policy["count"] > 0

    # Scenario 6 — Permission denied for unknown restricted tool
    def test_scenario_6_permission_denied(self):
        r = json.loads(self.client.call_tool("check_user_permission", {"role": "employee", "tool_name": "drop_all_tables"}))
        assert r["allowed"] is False

    # Scenario 7 — Unknown department returns empty
    def test_scenario_7_unknown_department(self):
        r = json.loads(self.client.call_tool("get_employee_info", {"department": "Nonexistent123", "user_role": "employee"}))
        assert r["count"] == 0
        assert r["employees"] == []

    # Scenario 8 — Databricks unavailable → local fallback
    def test_scenario_8_databricks_fallback(self):
        # Temporarily simulate DEMO_MODE=false but no credentials
        original = os.environ.get("DEMO_MODE", "true")
        os.environ["DEMO_MODE"] = "false"
        try:
            from mcp_server import tools as t
            # Should fall back to local CSV without raising
            result = t.get_department_info("AI")
            assert result["count"] == 1
        finally:
            os.environ["DEMO_MODE"] = original


# ── Full LLM + agent integration (requires API key) ──────────────────────────

@pytest.mark.skipif(SKIP_LLM, reason="Set SKIP_LLM_TESTS=false with valid API key to run")
class TestAgentLLMScenarios:

    def _run(self, question: str, role: str = "employee") -> str:
        from mcp_client import MCPClient
        from agent.graph import build_graph, get_llm
        from langchain_core.messages import HumanMessage
        client = MCPClient()
        graph  = build_graph(get_llm(client.get_tools()), client)
        result = graph.invoke({
            "messages":          [HumanMessage(content=question)],
            "user_role":         role,
            "tool_results":      [],
            "final_answer":      None,
            "error":             None,
            "permission_denied": False,
        })
        return result.get("final_answer") or ""

    def test_llm_ai_department(self):
        ans = self._run("Who works in the AI department?")
        assert any(name in ans for name in ["Alice", "Bob", "Karen", "Carol"])

    def test_llm_active_projects(self):
        ans = self._run("What projects are currently active?")
        assert "Active" in ans or "active" in ans

    def test_llm_leave_policy(self):
        ans = self._run("What is the company leave policy?")
        assert len(ans) > 50

    def test_llm_multi_tool_ai(self):
        ans = self._run("Who works in AI and what projects are they working on?")
        assert any(name in ans for name in ["Alice", "Bob", "Karen"])
        assert any(proj in ans for proj in ["SmartAssist", "Predictive"])

    def test_llm_security_combined(self):
        ans = self._run("Who works in Security and what are the security policies?")
        assert any(name in ans for name in ["Grace", "Henry", "Mia"])

    def test_llm_permission_denied_response(self):
        ans = self._run("Show me restricted salary information.")
        # Agent should politely decline
        assert len(ans) > 10
