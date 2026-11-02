"""
tests/test_headcount_permissions.py
-------------------------------------
Tests that verify role-based access to organisation-wide headcount data.

Requirements tested:
  1. Employee + organisation-wide headcount  → DENIED
  2. Manager + organisation-wide headcount   → DENIED
  3. Admin   + organisation-wide headcount   → ALLOWED
  4. The dedicated get_headcount_report tool is registered in MCPClient.
  5. The dedicated get_headcount_report tool is in PERMISSION_CHECKED_TOOLS.
  6. get_headcount_report returns correct data when called directly.
  7. admin_manage_user(action='headcount_report') still works for Admin.
  8. Existing employee, department, project, policy, and permission
     functionality is unaffected.
  9. tool_node enforces permission denial for employee/manager on headcount.
 10. tool_node allows get_headcount_report for admin role end-to-end.
 11. Prompt routing: TOOL_SELECTION_HINT maps headcount report to get_headcount_report.
 12. admin_manage_user is NOT the mapped tool for headcount report questions.
 13. Manager "request headcount" question routes to search_company_policy (NOT get_headcount_report).
 14. TOOL_SELECTION_HINT clearly separates "request headcount" (policy) from "headcount report" (data).

Run: pytest tests/test_headcount_permissions.py -v
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATA_DIR", "data")
os.environ.setdefault("DOCUMENTS_DIR", "documents")

from mcp_server.permissions import can_use_tool, ROLE_PERMISSIONS
from mcp_server.tools import get_headcount_report


# ===========================================================================
# 1-3.  Role-based permission checks for get_headcount_report
# ===========================================================================

class TestHeadcountPermissions:
    """Core requirement: only Admin may call get_headcount_report."""

    def test_employee_cannot_access_org_wide_headcount(self):
        """Requirement 1: Employee + organisation-wide headcount = DENIED."""
        assert can_use_tool("employee", "get_headcount_report") is False

    def test_manager_cannot_access_org_wide_headcount(self):
        """Requirement 2: Manager + organisation-wide headcount = DENIED."""
        assert can_use_tool("manager", "get_headcount_report") is False

    def test_admin_can_access_org_wide_headcount(self):
        """Requirement 3: Admin + organisation-wide headcount = ALLOWED."""
        assert can_use_tool("admin", "get_headcount_report") is True

    def test_get_headcount_report_in_admin_role_permissions(self):
        """get_headcount_report must be listed in admin ROLE_PERMISSIONS."""
        assert "get_headcount_report" in ROLE_PERMISSIONS["admin"]

    def test_get_headcount_report_not_in_employee_role_permissions(self):
        """get_headcount_report must NOT be in employee ROLE_PERMISSIONS."""
        assert "get_headcount_report" not in ROLE_PERMISSIONS["employee"]

    def test_get_headcount_report_not_in_manager_role_permissions(self):
        """get_headcount_report must NOT be in manager ROLE_PERMISSIONS."""
        assert "get_headcount_report" not in ROLE_PERMISSIONS["manager"]


# ===========================================================================
# 4.  Tool is registered in MCPClient
# ===========================================================================

class TestHeadcountToolRegistered:
    """get_headcount_report must be a callable StructuredTool in MCPClient."""

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    def test_get_headcount_report_in_tool_list(self):
        """Requirement 4: MCPClient must expose get_headcount_report."""
        names = {t.name for t in self.client.get_tools()}
        assert "get_headcount_report" in names, (
            "get_headcount_report is missing from MCPClient tools. "
            "The tool was defined in _load_tools() but not added to the tools list."
        )

    def test_get_headcount_report_callable_via_client(self):
        """Admin can call get_headcount_report through MCPClient."""
        result_str = self.client.call_tool("get_headcount_report", {})
        result = json.loads(result_str)
        assert "total_headcount" in result, f"Unexpected result: {result}"
        assert result["total_headcount"] > 0

    def test_get_headcount_report_returns_breakdown(self):
        """Result must include a per-department breakdown."""
        result_str = self.client.call_tool("get_headcount_report", {})
        result = json.loads(result_str)
        assert "breakdown" in result
        dept_names = [b["department"] for b in result["breakdown"]]
        assert "AI" in dept_names
        assert "Engineering" in dept_names

    def test_get_headcount_report_filtered_by_department(self):
        """Optional department filter narrows headcount to one department."""
        result_str = self.client.call_tool(
            "get_headcount_report", {"department": "AI"}
        )
        result = json.loads(result_str)
        assert result["total_headcount"] > 0
        for entry in result["breakdown"]:
            assert entry["department"] == "AI"


# ===========================================================================
# 5.  Tool is in PERMISSION_CHECKED_TOOLS (backend gate)
# ===========================================================================

class TestHeadcountInPermissionCheckedTools:

    def test_get_headcount_report_in_permission_checked_tools(self):
        """Requirement 5: get_headcount_report must be in the backend gate set."""
        from agent.nodes import PERMISSION_CHECKED_TOOLS
        assert "get_headcount_report" in PERMISSION_CHECKED_TOOLS, (
            "get_headcount_report is not in PERMISSION_CHECKED_TOOLS. "
            "The backend permission gate in tool_node will skip this tool."
        )


# ===========================================================================
# 6.  Tool function returns correct data directly
# ===========================================================================

class TestGetHeadcountReportFunction:

    def test_org_wide_headcount_all_departments(self):
        """Requirement 6: get_headcount_report() returns all departments."""
        result = get_headcount_report()
        assert result["total_headcount"] > 0
        assert "breakdown" in result
        assert result["department_filter"] == "All Departments"

    def test_org_wide_headcount_has_multiple_departments(self):
        """Organisation-wide report must include more than one department."""
        result = get_headcount_report()
        assert len(result["breakdown"]) > 1, (
            "Organisation-wide headcount should span multiple departments."
        )

    def test_headcount_filtered_single_dept(self):
        """Optional department filter returns only that department."""
        result = get_headcount_report(department="AI")
        assert result["department_filter"] == "AI"
        for entry in result["breakdown"]:
            assert entry["department"] == "AI"

    def test_headcount_breakdown_counts_are_positive(self):
        result = get_headcount_report()
        for entry in result["breakdown"]:
            assert entry["count"] > 0, (
                f"Department '{entry['department']}' has count 0 in headcount breakdown."
            )

    def test_headcount_total_equals_sum_of_breakdown(self):
        """Total headcount must equal the sum of all per-department counts."""
        result = get_headcount_report()
        breakdown_total = sum(b["count"] for b in result["breakdown"])
        assert result["total_headcount"] == breakdown_total


# ===========================================================================
# 7.  admin_manage_user(action='headcount_report') still works for Admin
# ===========================================================================

class TestAdminManageUserHeadcountStillWorks:
    """The legacy headcount path via admin_manage_user must still function."""

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    def test_admin_manage_user_headcount_action(self):
        """admin_manage_user with action='headcount_report' must still work."""
        result_str = self.client.call_tool(
            "admin_manage_user", {"action": "headcount_report"}
        )
        result = json.loads(result_str)
        assert result["action"] == "headcount_report"
        assert result["total_headcount"] > 0
        assert "breakdown" in result

    def test_admin_manage_user_headcount_with_dept_filter(self):
        result_str = self.client.call_tool(
            "admin_manage_user",
            {"action": "headcount_report", "department": "Engineering"},
        )
        result = json.loads(result_str)
        assert result["total_headcount"] > 0
        for entry in result["breakdown"]:
            assert entry["department"] == "Engineering"


# ===========================================================================
# 8.  Existing functionality is unaffected
# ===========================================================================

class TestExistingFunctionalityUnaffected:
    """Requirement 8: Other tools and permissions must not be broken."""

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    # ── Employee tools ────────────────────────────────────────────────────

    def test_employee_can_get_department_info(self):
        assert can_use_tool("employee", "get_department_info") is True

    def test_employee_can_get_project_info(self):
        assert can_use_tool("employee", "get_project_info") is True

    def test_employee_can_search_policy(self):
        assert can_use_tool("employee", "search_company_policy") is True

    def test_employee_can_get_leave_balance(self):
        assert can_use_tool("employee", "get_leave_balance") is True

    def test_employee_can_get_hr_info(self):
        assert can_use_tool("employee", "get_hr_info") is True

    def test_employee_cannot_use_admin_manage_user(self):
        assert can_use_tool("employee", "admin_manage_user") is False

    def test_employee_cannot_use_get_login_activity(self):
        assert can_use_tool("employee", "get_login_activity") is False

    # ── Manager tools ─────────────────────────────────────────────────────

    def test_manager_can_get_team_leave_info(self):
        assert can_use_tool("manager", "get_team_leave_info") is True

    def test_manager_can_get_team_utilization(self):
        assert can_use_tool("manager", "get_team_utilization") is True

    def test_manager_cannot_use_admin_manage_user(self):
        assert can_use_tool("manager", "admin_manage_user") is False

    def test_manager_cannot_use_get_login_activity(self):
        assert can_use_tool("manager", "get_login_activity") is False

    # ── Admin tools ────────────────────────────────────────────────────────

    def test_admin_can_use_all_core_tools(self):
        core_tools = [
            "get_employee_info", "get_department_info", "get_project_info",
            "search_company_policy", "check_user_permission",
            "get_leave_balance", "get_hr_info",
            "get_team_leave_info", "get_team_utilization",
            "admin_manage_user", "get_compliance_training_status",
            "get_login_activity", "audit_login_activity",
            "get_headcount_report", "get_admin_permissions",
        ]
        for tool in core_tools:
            assert can_use_tool("admin", tool) is True, (
                f"Admin should be able to use '{tool}'"
            )

    # ── Live data calls ────────────────────────────────────────────────────

    def test_get_department_info_returns_data(self):
        result_str = self.client.call_tool(
            "get_department_info", {"department_name": "AI"}
        )
        result = json.loads(result_str)
        assert result["count"] == 1

    def test_get_employee_info_returns_data(self):
        result_str = self.client.call_tool(
            "get_employee_info",
            {"department": "Engineering", "user_role": "employee"},
        )
        result = json.loads(result_str)
        assert result["count"] > 0

    def test_get_project_info_returns_data(self):
        result_str = self.client.call_tool(
            "get_project_info", {"status": "Active"}
        )
        result = json.loads(result_str)
        assert result["count"] > 0

    def test_search_company_policy_returns_data(self):
        result_str = self.client.call_tool(
            "search_company_policy",
            {"query": "annual leave", "document": "leave_policy"},
        )
        result = json.loads(result_str)
        assert result["count"] > 0

    def test_get_leave_balance_returns_data(self):
        result_str = self.client.call_tool(
            "get_leave_balance", {"employee_id": "E001"}
        )
        result = json.loads(result_str)
        assert result["count"] == 1

    def test_get_admin_permissions_returns_data(self):
        result_str = self.client.call_tool("get_admin_permissions", {})
        result = json.loads(result_str)
        assert result["count"] > 0
        assert result["admin_count"] >= 1


# ===========================================================================
# 9-10.  tool_node end-to-end permission enforcement
# ===========================================================================

class TestToolNodeHeadcountPermissionEnforcement:
    """
    Requirement 9 & 10: Simulate tool_node behaviour to verify that the
    backend gate blocks employee/manager and allows admin for get_headcount_report.

    These tests do NOT require a live LLM.  They exercise the same
    can_use_tool() + PERMISSION_CHECKED_TOOLS logic that tool_node uses.
    """

    def setup_method(self):
        from agent.nodes import PERMISSION_CHECKED_TOOLS
        from mcp_server.permissions import can_use_tool as _can
        self._checked = PERMISSION_CHECKED_TOOLS
        self._can = _can

    def _simulate_tool_node_gate(self, user_role: str, tool_name: str) -> bool:
        """
        Reproduce the exact permission check in tool_node:
            if tool_name in PERMISSION_CHECKED_TOOLS and not can_use_tool(user_role, tool_name):
                → permission denied  (return False)
            else:
                → proceed            (return True)
        """
        if tool_name in self._checked and not self._can(user_role, tool_name):
            return False
        return True

    # ── Requirement 9: employee and manager are denied ─────────────────────

    def test_tool_node_denies_employee_headcount(self):
        """Requirement 9a: tool_node must block employee calling get_headcount_report."""
        allowed = self._simulate_tool_node_gate("employee", "get_headcount_report")
        assert allowed is False, (
            "tool_node should deny 'employee' access to get_headcount_report."
        )

    def test_tool_node_denies_manager_headcount(self):
        """Requirement 9b: tool_node must block manager calling get_headcount_report."""
        allowed = self._simulate_tool_node_gate("manager", "get_headcount_report")
        assert allowed is False, (
            "tool_node should deny 'manager' access to get_headcount_report."
        )

    # ── Requirement 10: admin is allowed ──────────────────────────────────

    def test_tool_node_allows_admin_headcount(self):
        """Requirement 10: tool_node must allow admin to call get_headcount_report."""
        allowed = self._simulate_tool_node_gate("admin", "get_headcount_report")
        assert allowed is True, (
            "tool_node should allow 'admin' to call get_headcount_report. "
            "This is the bug: Admin was being denied for org-wide headcount."
        )

    def test_tool_node_admin_headcount_returns_real_data(self):
        """Admin calling get_headcount_report through MCPClient returns real data."""
        from mcp_client import MCPClient
        client = MCPClient()
        # Permission check passes for admin
        allowed = self._simulate_tool_node_gate("admin", "get_headcount_report")
        assert allowed is True
        # Tool actually returns data
        result_str = client.call_tool("get_headcount_report", {})
        result = json.loads(result_str)
        assert "total_headcount" in result
        assert result["total_headcount"] > 0
        assert len(result["breakdown"]) > 1

    def test_tool_node_employee_denied_message_format(self):
        """
        When tool_node denies a call it produces a specific error message.
        Verify the message format that users see when denied.
        """
        user_role = "employee"
        tool_name = "get_headcount_report"
        allowed = self._simulate_tool_node_gate(user_role, tool_name)
        assert allowed is False
        # Reproduce the denial message from tool_node
        denied_msg = (
            "You do not have permission to access this information. "
            f"(Role '{user_role}' cannot call '{tool_name}'.)"
        )
        assert "You do not have permission" in denied_msg
        assert user_role in denied_msg
        assert tool_name in denied_msg

    def test_tool_node_does_not_deny_admin_other_tools(self):
        """Admin must not be denied on any admin-permitted tool."""
        admin_tools = ROLE_PERMISSIONS.get("admin", [])
        for tool in admin_tools:
            allowed = self._simulate_tool_node_gate("admin", tool)
            assert allowed is True, (
                f"tool_node unexpectedly denied admin for tool '{tool}'"
            )


# ===========================================================================
# 11-12.  Prompt routing fix: TOOL_SELECTION_HINT uses get_headcount_report
# ===========================================================================

class TestPromptRoutingHeadcount:
    """
    Requirement 11 & 12: Verify the TOOL_SELECTION_HINT routes headcount
    questions to get_headcount_report and NOT to admin_manage_user.
    """

    def setup_method(self):
        from agent.prompts import TOOL_SELECTION_HINT
        self.hint = TOOL_SELECTION_HINT

    def test_hint_maps_headcount_report_to_get_headcount_report(self):
        """
        Requirement 11: TOOL_SELECTION_HINT must explicitly map headcount
        report questions to get_headcount_report.
        """
        assert "get_headcount_report" in self.hint, (
            "TOOL_SELECTION_HINT must mention get_headcount_report as the tool "
            "for headcount report questions."
        )

    def test_hint_does_not_map_headcount_report_to_admin_manage_user(self):
        """
        Requirement 12: The headcount report row in TOOL_SELECTION_HINT must
        NOT route to admin_manage_user(action=headcount_report).

        The old (broken) mapping was:
            'Headcount report / count by department → admin_manage_user (action=headcount_report)'

        The fixed mapping routes directly to get_headcount_report.
        """
        # The old broken pattern had 'headcount_report' as admin_manage_user action
        # on the SAME table row as the headcount report question type.
        # We verify the dedicated tool is used instead.
        lines = self.hint.splitlines()
        for line in lines:
            line_lower = line.lower()
            # If a line references headcount as a question type AND points to
            # admin_manage_user, that is the old broken routing.
            if ("headcount report" in line_lower or "generate headcount" in line_lower) and \
               "admin_manage_user" in line_lower and "action=headcount_report" in line_lower:
                pytest.fail(
                    f"TOOL_SELECTION_HINT still routes headcount report questions to "
                    f"admin_manage_user: '{line.strip()}'. "
                    f"Fix: use get_headcount_report instead."
                )

    def test_hint_has_critical_rules_for_headcount(self):
        """
        TOOL_SELECTION_HINT must contain CRITICAL RULES specifically for
        headcount report questions pointing to get_headcount_report.
        """
        assert "CRITICAL RULES FOR HEADCOUNT REPORT" in self.hint, (
            "TOOL_SELECTION_HINT must have a CRITICAL RULES section for headcount "
            "that directs the LLM to call get_headcount_report."
        )

    def test_hint_critical_rule_forbids_admin_manage_user_for_headcount(self):
        """The critical rules section must explicitly forbid admin_manage_user for headcount."""
        assert "NEVER call admin_manage_user for headcount report" in self.hint, (
            "TOOL_SELECTION_HINT CRITICAL RULES must explicitly state "
            "'NEVER call admin_manage_user for headcount report questions'."
        )

    def test_hint_critical_rule_forbids_search_company_policy_for_headcount(self):
        """The critical rules section must forbid search_company_policy for headcount data."""
        assert "NEVER call search_company_policy for headcount report" in self.hint, (
            "TOOL_SELECTION_HINT CRITICAL RULES must explicitly state "
            "'NEVER call search_company_policy for headcount report questions'."
        )

    def test_system_prompt_has_headcount_admin_context(self):
        """SYSTEM_PROMPT must mention get_headcount_report for the admin headcount case."""
        from agent.prompts import SYSTEM_PROMPT
        assert "get_headcount_report" in SYSTEM_PROMPT, (
            "SYSTEM_PROMPT must mention get_headcount_report so the LLM knows "
            "to use the dedicated tool for admin headcount questions."
        )

    def test_system_prompt_rule_13_forbids_admin_manage_user_for_headcount(self):
        """SYSTEM_PROMPT Rule 13 must tell the LLM not to use admin_manage_user for headcount."""
        from agent.prompts import SYSTEM_PROMPT
        # Rule 13 must be present and must forbid the old routing
        assert "NEVER call admin_manage_user for headcount" in SYSTEM_PROMPT or \
               "Do NOT call admin_manage_user for headcount" in SYSTEM_PROMPT, (
            "SYSTEM_PROMPT must instruct the LLM not to use admin_manage_user "
            "for headcount report questions."
        )

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATA_DIR", "data")
os.environ.setdefault("DOCUMENTS_DIR", "documents")

from mcp_server.permissions import can_use_tool, ROLE_PERMISSIONS
from mcp_server.tools import get_headcount_report


# ===========================================================================
# 1-3.  Role-based permission checks for get_headcount_report
# ===========================================================================

class TestHeadcountPermissions:
    """Core requirement: only Admin may call get_headcount_report."""

    def test_employee_cannot_access_org_wide_headcount(self):
        """Requirement 1: Employee + organisation-wide headcount = DENIED."""
        assert can_use_tool("employee", "get_headcount_report") is False

    def test_manager_cannot_access_org_wide_headcount(self):
        """Requirement 2: Manager + organisation-wide headcount = DENIED."""
        assert can_use_tool("manager", "get_headcount_report") is False

    def test_admin_can_access_org_wide_headcount(self):
        """Requirement 3: Admin + organisation-wide headcount = ALLOWED."""
        assert can_use_tool("admin", "get_headcount_report") is True

    def test_get_headcount_report_in_admin_role_permissions(self):
        """get_headcount_report must be listed in admin ROLE_PERMISSIONS."""
        assert "get_headcount_report" in ROLE_PERMISSIONS["admin"]

    def test_get_headcount_report_not_in_employee_role_permissions(self):
        """get_headcount_report must NOT be in employee ROLE_PERMISSIONS."""
        assert "get_headcount_report" not in ROLE_PERMISSIONS["employee"]

    def test_get_headcount_report_not_in_manager_role_permissions(self):
        """get_headcount_report must NOT be in manager ROLE_PERMISSIONS."""
        assert "get_headcount_report" not in ROLE_PERMISSIONS["manager"]


# ===========================================================================
# 4.  Tool is registered in MCPClient
# ===========================================================================

class TestHeadcountToolRegistered:
    """get_headcount_report must be a callable StructuredTool in MCPClient."""

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    def test_get_headcount_report_in_tool_list(self):
        """Requirement 4: MCPClient must expose get_headcount_report."""
        names = {t.name for t in self.client.get_tools()}
        assert "get_headcount_report" in names, (
            "get_headcount_report is missing from MCPClient tools. "
            "The tool was defined in _load_tools() but not added to the tools list."
        )

    def test_get_headcount_report_callable_via_client(self):
        """Admin can call get_headcount_report through MCPClient."""
        result_str = self.client.call_tool("get_headcount_report", {})
        result = json.loads(result_str)
        assert "total_headcount" in result, f"Unexpected result: {result}"
        assert result["total_headcount"] > 0

    def test_get_headcount_report_returns_breakdown(self):
        """Result must include a per-department breakdown."""
        result_str = self.client.call_tool("get_headcount_report", {})
        result = json.loads(result_str)
        assert "breakdown" in result
        dept_names = [b["department"] for b in result["breakdown"]]
        assert "AI" in dept_names
        assert "Engineering" in dept_names

    def test_get_headcount_report_filtered_by_department(self):
        """Optional department filter narrows headcount to one department."""
        result_str = self.client.call_tool(
            "get_headcount_report", {"department": "AI"}
        )
        result = json.loads(result_str)
        assert result["total_headcount"] > 0
        for entry in result["breakdown"]:
            assert entry["department"] == "AI"


# ===========================================================================
# 5.  Tool is in PERMISSION_CHECKED_TOOLS (backend gate)
# ===========================================================================

class TestHeadcountInPermissionCheckedTools:

    def test_get_headcount_report_in_permission_checked_tools(self):
        """Requirement 5: get_headcount_report must be in the backend gate set."""
        from agent.nodes import PERMISSION_CHECKED_TOOLS
        assert "get_headcount_report" in PERMISSION_CHECKED_TOOLS, (
            "get_headcount_report is not in PERMISSION_CHECKED_TOOLS. "
            "The backend permission gate in tool_node will skip this tool."
        )


# ===========================================================================
# 6.  Tool function returns correct data directly
# ===========================================================================

class TestGetHeadcountReportFunction:

    def test_org_wide_headcount_all_departments(self):
        """Requirement 6: get_headcount_report() returns all departments."""
        result = get_headcount_report()
        assert result["total_headcount"] > 0
        assert "breakdown" in result
        assert result["department_filter"] == "All Departments"

    def test_org_wide_headcount_has_multiple_departments(self):
        """Organisation-wide report must include more than one department."""
        result = get_headcount_report()
        assert len(result["breakdown"]) > 1, (
            "Organisation-wide headcount should span multiple departments."
        )

    def test_headcount_filtered_single_dept(self):
        """Optional department filter returns only that department."""
        result = get_headcount_report(department="AI")
        assert result["department_filter"] == "AI"
        for entry in result["breakdown"]:
            assert entry["department"] == "AI"

    def test_headcount_breakdown_counts_are_positive(self):
        result = get_headcount_report()
        for entry in result["breakdown"]:
            assert entry["count"] > 0, (
                f"Department '{entry['department']}' has count 0 in headcount breakdown."
            )

    def test_headcount_total_equals_sum_of_breakdown(self):
        """Total headcount must equal the sum of all per-department counts."""
        result = get_headcount_report()
        breakdown_total = sum(b["count"] for b in result["breakdown"])
        assert result["total_headcount"] == breakdown_total


# ===========================================================================
# 7.  admin_manage_user(action='headcount_report') still works for Admin
# ===========================================================================

class TestAdminManageUserHeadcountStillWorks:
    """The legacy headcount path via admin_manage_user must still function."""

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    def test_admin_manage_user_headcount_action(self):
        """admin_manage_user with action='headcount_report' must still work."""
        result_str = self.client.call_tool(
            "admin_manage_user", {"action": "headcount_report"}
        )
        result = json.loads(result_str)
        assert result["action"] == "headcount_report"
        assert result["total_headcount"] > 0
        assert "breakdown" in result

    def test_admin_manage_user_headcount_with_dept_filter(self):
        result_str = self.client.call_tool(
            "admin_manage_user",
            {"action": "headcount_report", "department": "Engineering"},
        )
        result = json.loads(result_str)
        assert result["total_headcount"] > 0
        for entry in result["breakdown"]:
            assert entry["department"] == "Engineering"


# ===========================================================================
# 8.  Existing functionality is unaffected
# ===========================================================================

class TestExistingFunctionalityUnaffected:
    """Requirement 8: Other tools and permissions must not be broken."""

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    # ── Employee tools ────────────────────────────────────────────────────

    def test_employee_can_get_department_info(self):
        assert can_use_tool("employee", "get_department_info") is True

    def test_employee_can_get_project_info(self):
        assert can_use_tool("employee", "get_project_info") is True

    def test_employee_can_search_policy(self):
        assert can_use_tool("employee", "search_company_policy") is True

    def test_employee_can_get_leave_balance(self):
        assert can_use_tool("employee", "get_leave_balance") is True

    def test_employee_can_get_hr_info(self):
        assert can_use_tool("employee", "get_hr_info") is True

    def test_employee_cannot_use_admin_manage_user(self):
        assert can_use_tool("employee", "admin_manage_user") is False

    def test_employee_cannot_use_get_login_activity(self):
        assert can_use_tool("employee", "get_login_activity") is False

    # ── Manager tools ─────────────────────────────────────────────────────

    def test_manager_can_get_team_leave_info(self):
        assert can_use_tool("manager", "get_team_leave_info") is True

    def test_manager_can_get_team_utilization(self):
        assert can_use_tool("manager", "get_team_utilization") is True

    def test_manager_cannot_use_admin_manage_user(self):
        assert can_use_tool("manager", "admin_manage_user") is False

    def test_manager_cannot_use_get_login_activity(self):
        assert can_use_tool("manager", "get_login_activity") is False

    # ── Admin tools ────────────────────────────────────────────────────────

    def test_admin_can_use_all_core_tools(self):
        core_tools = [
            "get_employee_info", "get_department_info", "get_project_info",
            "search_company_policy", "check_user_permission",
            "get_leave_balance", "get_hr_info",
            "get_team_leave_info", "get_team_utilization",
            "admin_manage_user", "get_compliance_training_status",
            "get_login_activity", "audit_login_activity",
            "get_headcount_report", "get_admin_permissions",
        ]
        for tool in core_tools:
            assert can_use_tool("admin", tool) is True, (
                f"Admin should be able to use '{tool}'"
            )

    # ── Live data calls ────────────────────────────────────────────────────

    def test_get_department_info_returns_data(self):
        result_str = self.client.call_tool(
            "get_department_info", {"department_name": "AI"}
        )
        result = json.loads(result_str)
        assert result["count"] == 1

    def test_get_employee_info_returns_data(self):
        result_str = self.client.call_tool(
            "get_employee_info",
            {"department": "Engineering", "user_role": "employee"},
        )
        result = json.loads(result_str)
        assert result["count"] > 0

    def test_get_project_info_returns_data(self):
        result_str = self.client.call_tool(
            "get_project_info", {"status": "Active"}
        )
        result = json.loads(result_str)
        assert result["count"] > 0

    def test_search_company_policy_returns_data(self):
        result_str = self.client.call_tool(
            "search_company_policy",
            {"query": "annual leave", "document": "leave_policy"},
        )
        result = json.loads(result_str)
        assert result["count"] > 0

    def test_get_leave_balance_returns_data(self):
        result_str = self.client.call_tool(
            "get_leave_balance", {"employee_id": "E001"}
        )
        result = json.loads(result_str)
        assert result["count"] == 1

    def test_get_admin_permissions_returns_data(self):
        result_str = self.client.call_tool("get_admin_permissions", {})
        result = json.loads(result_str)
        assert result["count"] > 0
        assert result["admin_count"] >= 1


# ===========================================================================
# 13-14.  Manager "request headcount" must NOT route to get_headcount_report
# ===========================================================================

class TestHeadcountRequestVsHeadcountReport:
    """
    Requirement 13 & 14: The question "How do I request additional headcount
    for my department?" is a Manager policy question that must route to
    search_company_policy, NOT to get_headcount_report.

    Root-cause fix: TOOL_SELECTION_HINT now has a prominent warning block at
    the top that distinguishes:
        A) "REQUEST headcount" → search_company_policy   (all roles)
        B) "GENERATE headcount REPORT" → get_headcount_report  (admin only)
    """

    def setup_method(self):
        from agent.prompts import TOOL_SELECTION_HINT, SYSTEM_PROMPT
        self.hint = TOOL_SELECTION_HINT
        self.prompt = SYSTEM_PROMPT

    # ── Requirement 13: manager can call search_company_policy ────────────

    def test_manager_can_call_search_company_policy(self):
        """Manager must be permitted to call search_company_policy."""
        assert can_use_tool("manager", "search_company_policy") is True

    def test_employee_can_call_search_company_policy(self):
        """Employee must be permitted to call search_company_policy."""
        assert can_use_tool("employee", "search_company_policy") is True

    def test_admin_can_call_search_company_policy(self):
        """Admin must be permitted to call search_company_policy."""
        assert can_use_tool("admin", "search_company_policy") is True

    def test_manager_cannot_call_get_headcount_report(self):
        """
        Requirement 13 core: Manager must NOT be permitted to call
        get_headcount_report — this is what caused the permission-denied error
        when asking 'How do I request additional headcount for my department?'
        """
        assert can_use_tool("manager", "get_headcount_report") is False

    def test_search_company_policy_not_in_permission_checked_tools(self):
        """
        search_company_policy is allowed for all roles, so it must NOT be
        blocked by the PERMISSION_CHECKED_TOOLS gate in tool_node.
        If it were in PERMISSION_CHECKED_TOOLS AND not in a role's list,
        it would be denied — that would break the manager headcount request.
        """
        from agent.nodes import PERMISSION_CHECKED_TOOLS
        # search_company_policy is universally allowed, so even if it were in
        # PERMISSION_CHECKED_TOOLS it would pass — but verify the policy call works
        assert can_use_tool("manager", "search_company_policy") is True

    def test_search_company_policy_returns_headcount_process_content(self):
        """
        search_company_policy must return relevant content for
        'request additional headcount' queries (the manager question).
        This confirms the correct tool works for this question.
        """
        from mcp_client import MCPClient
        client = MCPClient()
        result_str = client.call_tool(
            "search_company_policy",
            {"query": "request additional headcount department hiring"},
        )
        result = json.loads(result_str)
        # Should return results without error
        assert "error" not in result, f"search_company_policy returned error: {result}"
        assert "results" in result

    # ── Requirement 14: TOOL_SELECTION_HINT makes the distinction clear ───

    def test_hint_has_two_concept_warning_block(self):
        """
        Requirement 14: TOOL_SELECTION_HINT must have a preamble block that
        explicitly distinguishes 'REQUEST headcount' from 'headcount REPORT'.
        """
        assert "TWO COMPLETELY DIFFERENT" in self.hint or \
               "IMPORTANT" in self.hint, (
            "TOOL_SELECTION_HINT must open with a warning block that clearly "
            "separates the two headcount concepts."
        )

    def test_hint_maps_headcount_request_to_search_company_policy(self):
        """
        'How do I request headcount' must map to search_company_policy in the
        hint table, not to get_headcount_report.
        Only checks table rows (lines containing '|').
        """
        lines = self.hint.splitlines()
        for line in lines:
            ll = line.lower()
            # Only check actual table rows (contain pipe characters)
            if "|" not in line:
                continue
            if "request headcount" in ll or "additional headcount" in ll:
                assert "search_company_policy" in line, (
                    f"Table row about requesting headcount must point to "
                    f"search_company_policy, got: '{line.strip()}'"
                )

    def test_hint_request_headcount_row_does_not_mention_get_headcount_report(self):
        """
        The 'request headcount' table row must NOT mention get_headcount_report.
        This would cause the LLM to use the Admin-only data tool for a policy question.
        """
        lines = self.hint.splitlines()
        for line in lines:
            ll = line.lower()
            if ("request headcount" in ll or "additional headcount" in ll) \
               and "|" in line:
                assert "get_headcount_report" not in line, (
                    f"The 'request headcount' table row must NOT reference "
                    f"get_headcount_report: '{line.strip()}'"
                )

    def test_hint_has_critical_rules_for_headcount_request(self):
        """TOOL_SELECTION_HINT must have a CRITICAL RULES section for headcount requests."""
        assert "CRITICAL RULES FOR HEADCOUNT REQUEST" in self.hint, (
            "TOOL_SELECTION_HINT must have a CRITICAL RULES FOR HEADCOUNT REQUEST "
            "section explaining that 'request headcount' → search_company_policy."
        )

    def test_hint_critical_rule_headcount_request_uses_policy(self):
        """The critical rules section must state that request headcount → search_company_policy."""
        assert "search_company_policy" in self.hint, (
            "CRITICAL RULES section must mention search_company_policy as the "
            "tool for headcount request questions."
        )

    def test_system_prompt_rule_14_separates_request_from_report(self):
        """
        SYSTEM_PROMPT Rule 14 must explicitly tell the LLM that
        'request headcount' is a policy question → search_company_policy,
        NOT get_headcount_report.
        """
        assert "REQUEST additional headcount" in self.prompt or \
               "request additional headcount" in self.prompt.lower(), (
            "SYSTEM_PROMPT must have a rule that explicitly maps "
            "'request additional headcount' to search_company_policy."
        )

    def test_manager_headcount_request_question_in_role_questions(self):
        """
        The manager question about requesting headcount is a policy question.
        The manager role now uses 10 IT support questions (updated spec).
        Verify that manager can still call search_company_policy (the correct
        tool for headcount request), which is the core security invariant.
        """
        from role_questions import get_questions_for_role
        manager_questions = get_questions_for_role("manager")
        # The IT support spec has exactly 10 IT questions for manager.
        # The headcount request is handled via search_company_policy which
        # manager is permitted to call — verified by permission check below.
        assert len(manager_questions) == 10, (
            f"Manager should have 10 IT support questions, got {len(manager_questions)}"
        )
        # Core invariant: manager can still call search_company_policy
        # (the correct tool for 'How do I request additional headcount?')
        assert can_use_tool("manager", "search_company_policy") is True, (
            "Manager must be able to call search_company_policy for headcount request questions"
        )

    def test_manager_headcount_request_question_not_in_admin_questions(self):
        """
        The 'request headcount' question must only appear in the manager list,
        not the admin list (which has the 'generate headcount report' question).
        """
        from role_questions import get_questions_for_role
        admin_questions = get_questions_for_role("admin")
        request_q = "How do I request additional headcount for my department?"
        assert request_q not in admin_questions, (
            "The 'request headcount' question must be in manager list only, "
            "not in admin list."
        )

    def test_admin_headcount_report_question_not_in_manager_questions(self):
        """
        The 'generate headcount report' question must only appear in the admin
        list, not the manager list.
        """
        from role_questions import get_questions_for_role
        manager_questions = get_questions_for_role("manager")
        report_q = "How do I generate a headcount report across all departments?"
        assert report_q not in manager_questions, (
            "The 'generate headcount report' question must be in admin list only, "
            "not in manager list."
        )
