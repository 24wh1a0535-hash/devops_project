"""
tests/test_agent.py
--------------------
Tests for the MCP client and basic agent workflow.

These tests verify:
- MCPClient loads tools correctly
- Each tool can be called through MCPClient
- Tools return expected structure
- The LangGraph graph builds without error

NOTE: LLM integration tests require a valid API key.
      Set SKIP_LLM_TESTS=true to skip them in environments without API keys.

Run: pytest tests/test_agent.py -v
"""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ["DEMO_MODE"] = "true"
os.environ["DATA_DIR"] = "data"
os.environ["DOCUMENTS_DIR"] = "documents"

SKIP_LLM = os.getenv("SKIP_LLM_TESTS", "true").lower() == "true"


# ===========================================================================
# MCPClient tests
# ===========================================================================

class TestMCPClient:

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    def test_client_loads_tools(self):
        tools = self.client.get_tools()
        # 16 original + 11 IT employee + 10 IT manager + 10 IT admin = 47
        assert len(tools) == 47

    def test_tool_names_are_correct(self):
        names = {t.name for t in self.client.get_tools()}
        expected = {
            # Original 16 tools
            "get_employee_info",
            "get_department_info",
            "get_project_info",
            "search_company_policy",
            "check_user_permission",
            "get_leave_balance",
            "get_hr_info",
            "get_team_leave_info",
            "get_team_attendance",
            "get_team_utilization",
            "admin_manage_user",
            "get_compliance_training_status",
            "get_login_activity",
            "audit_login_activity",
            "get_headcount_report",
            "get_admin_permissions",
            # IT support — employee (11)
            "check_active_incidents",
            "check_application_status",
            "check_vpn_status",
            "check_network_status",
            "check_user_application_access",
            "check_authentication_issue",
            "get_it_ticket_status",
            "get_it_ticket_assignee",
            "get_it_ticket_last_updated",
            "find_related_incident",
            "create_it_ticket",
            # IT support — manager (10)
            "get_team_incidents",
            "get_team_affected_users",
            "compare_incident_scope",
            "get_incident_status",
            "get_incident_owner",
            "get_incident_timeline",
            "get_incident_eta",
            "get_team_unresolved_tickets",
            "get_recurring_team_incidents",
            "escalate_incident",
            # IT support — admin (10)
            "get_active_incidents",
            "get_critical_service_status",
            "get_affected_offices_departments",
            "get_incident_impact",
            "get_incident_updates",
            "get_incident_responsible_team",
            "get_sla_breaches",
            "get_recurring_incidents",
            "find_duplicate_incidents",
            "get_incidents_requiring_escalation",
        }
        assert names == expected

    def test_call_get_department_info(self):
        result_str = self.client.call_tool("get_department_info", {"department_name": "AI"})
        result = json.loads(result_str)
        assert "departments" in result
        assert result["count"] == 1

    def test_call_get_employee_info(self):
        result_str = self.client.call_tool(
            "get_employee_info",
            {"department": "Engineering", "user_role": "employee"}
        )
        result = json.loads(result_str)
        assert "employees" in result
        assert result["count"] > 0

    def test_call_get_project_info(self):
        result_str = self.client.call_tool(
            "get_project_info",
            {"status": "Active"}
        )
        result = json.loads(result_str)
        assert "projects" in result
        assert result["count"] > 0

    def test_call_search_company_policy(self):
        result_str = self.client.call_tool(
            "search_company_policy",
            {"query": "maternity leave"}
        )
        result = json.loads(result_str)
        assert "results" in result

    def test_call_check_user_permission(self):
        result_str = self.client.call_tool(
            "check_user_permission",
            {"role": "employee", "tool_name": "get_department_info"}
        )
        result = json.loads(result_str)
        assert result["allowed"] is True

    def test_call_unknown_tool_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            self.client.call_tool("drop_database", {})

    def test_employee_cannot_see_access_level(self):
        result_str = self.client.call_tool(
            "get_employee_info",
            {"department": "AI", "user_role": "employee"}
        )
        result = json.loads(result_str)
        for emp in result["employees"]:
            assert "access_level" not in emp

    def test_admin_can_see_access_level(self):
        result_str = self.client.call_tool(
            "get_employee_info",
            {"department": "AI", "user_role": "admin"}
        )
        result = json.loads(result_str)
        for emp in result["employees"]:
            assert "access_level" in emp


# ===========================================================================
# LangGraph graph build test (no LLM call)
# ===========================================================================

class TestGraphBuild:

    def test_graph_compiles(self):
        """Verify the graph compiles without errors (no LLM call needed)."""
        from mcp_client import MCPClient
        from agent.graph import build_graph
        from unittest.mock import MagicMock

        client = MCPClient()
        tools = client.get_tools()

        # Mock LLM — we're just testing graph compilation
        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)

        graph = build_graph(mock_llm, client)
        assert graph is not None


# ===========================================================================
# LLM integration test (requires real API key)
# ===========================================================================

@pytest.mark.skipif(SKIP_LLM, reason="SKIP_LLM_TESTS=true — set to false and add API key to run")
class TestAgentIntegration:

    def test_agent_answers_department_question(self):
        from mcp_client import MCPClient
        from agent.graph import build_graph, get_llm
        from langchain_core.messages import HumanMessage

        client = MCPClient()
        tools = client.get_tools()
        llm = get_llm(tools)
        graph = build_graph(llm, client)

        result = graph.invoke({
            "messages": [HumanMessage(content="What departments exist at ACME Technologies?")],
            "user_role": "employee",
            "tool_results": [],
            "final_answer": None,
            "error": None,
        })

        assert result.get("final_answer") or any(
            hasattr(m, "content") and m.content
            for m in result.get("messages", [])
        )
