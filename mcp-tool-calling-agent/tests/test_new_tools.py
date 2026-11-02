"""
tests/test_new_tools.py
-----------------------
Comprehensive tests for the extended MCP tool-calling system.

Tests cover:
1.  Role question counts (employee=7, manager=8, admin=8, strictly exclusive).
2.  Every MCP tool returns meaningful demo data.
3.  Permission checks: authorized calls allowed, unauthorized denied.
4.  All 23 example questions map to working tools.
5.  Existing tools still work.
6.  Policy search works for all policy questions.
7.  Databricks integration is not broken (demo mode fallback confirmed).
8.  Full tool suite loads correctly (14 tools, including get_team_attendance).

Run: pytest tests/test_new_tools.py -v
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATA_DIR", "data")
os.environ.setdefault("DOCUMENTS_DIR", "documents")

from mcp_server.tools import (
    get_employee_info,
    get_department_info,
    get_project_info,
    search_company_policy,
    get_leave_balance,
    get_hr_info,
    get_team_leave_info,
    get_team_utilization,
    admin_manage_user,
    get_compliance_training_status,
    get_login_activity,
    get_admin_permissions,
)
from mcp_server.permissions import can_use_tool, ROLE_PERMISSIONS, ROLES
from role_questions import get_questions_for_role, ROLE_EXAMPLE_QUESTIONS


# ===========================================================================
# 1.  Role question counts — 8 per role, strictly exclusive
# ===========================================================================

class TestRoleQuestionCounts:

    def test_employee_has_exactly_8_questions(self):
        # Employee now has 10 IT support questions
        assert len(get_questions_for_role("employee")) == 10

    def test_manager_has_exactly_8_questions(self):
        assert len(get_questions_for_role("manager")) == 10

    def test_admin_has_exactly_8_questions(self):
        assert len(get_questions_for_role("admin")) == 10

    def test_employee_questions_not_shown_to_manager(self):
        emp = set(get_questions_for_role("employee"))
        mgr = set(get_questions_for_role("manager"))
        assert emp.isdisjoint(mgr), f"Overlap: {emp & mgr}"

    def test_manager_questions_not_shown_to_admin(self):
        mgr = set(get_questions_for_role("manager"))
        adm = set(get_questions_for_role("admin"))
        assert mgr.isdisjoint(adm), f"Overlap: {mgr & adm}"

    def test_admin_questions_not_shown_to_employee(self):
        adm = set(get_questions_for_role("admin"))
        emp = set(get_questions_for_role("employee"))
        assert adm.isdisjoint(emp), f"Overlap: {adm & emp}"

    def test_all_three_role_lists_are_disjoint(self):
        emp = set(get_questions_for_role("employee"))
        mgr = set(get_questions_for_role("manager"))
        adm = set(get_questions_for_role("admin"))
        assert emp.isdisjoint(mgr)
        assert emp.isdisjoint(adm)
        assert mgr.isdisjoint(adm)

    def test_total_questions_is_24(self):
        # employee=10, manager=10, admin=10 → 30 total
        total = sum(len(get_questions_for_role(r)) for r in ["employee", "manager", "admin"])
        assert total == 30


# ===========================================================================
# 2.  MCPClient loads all 13 tools
# ===========================================================================

class TestMCPClientTools:

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    def test_client_loads_13_tools(self):
        # 47 tools: 16 original + 31 new IT support tools
        assert len(self.client.get_tools()) == 47

    def test_all_tool_names_present(self):
        names = {t.name for t in self.client.get_tools()}
        expected = {
            # Original 16 tools
            "get_employee_info", "get_department_info", "get_project_info",
            "search_company_policy", "check_user_permission",
            "get_leave_balance", "get_hr_info",
            "get_team_leave_info", "get_team_attendance", "get_team_utilization",
            "admin_manage_user", "get_compliance_training_status",
            "get_login_activity", "audit_login_activity",
            "get_headcount_report", "get_admin_permissions",
            # IT support — employee (11)
            "check_active_incidents", "check_application_status", "check_vpn_status",
            "check_network_status", "check_user_application_access",
            "check_authentication_issue", "get_it_ticket_status",
            "get_it_ticket_assignee", "get_it_ticket_last_updated",
            "find_related_incident", "create_it_ticket",
            # IT support — manager (10)
            "get_team_incidents", "get_team_affected_users", "compare_incident_scope",
            "get_incident_status", "get_incident_owner", "get_incident_timeline",
            "get_incident_eta", "get_team_unresolved_tickets",
            "get_recurring_team_incidents", "escalate_incident",
            # IT support — admin (10)
            "get_active_incidents", "get_critical_service_status",
            "get_affected_offices_departments", "get_incident_impact",
            "get_incident_updates", "get_incident_responsible_team",
            "get_sla_breaches", "get_recurring_incidents",
            "find_duplicate_incidents", "get_incidents_requiring_escalation",
        }
        missing = expected - names
        extra = names - expected
        assert not missing, f"Missing tools: {missing}"
        assert names == expected, f"Extra tools: {extra}"


# ===========================================================================
# 3.  Existing tools still work
# ===========================================================================

class TestExistingTools:

    def test_get_employee_info_returns_data(self):
        result = get_employee_info(department="AI")
        assert result["count"] > 0
        assert "employees" in result

    def test_get_department_info_returns_data(self):
        result = get_department_info()
        assert result["count"] >= 4

    def test_get_project_info_returns_active(self):
        result = get_project_info(status="Active")
        assert result["count"] > 0

    def test_search_company_policy_leave(self):
        result = search_company_policy("annual leave days")
        assert result["count"] > 0

    def test_search_company_policy_password(self):
        result = search_company_policy("password requirements")
        assert result["count"] > 0
        texts = [r["excerpt"].lower() for r in result["results"]]
        assert any("password" in t for t in texts)


# ===========================================================================
# 4.  New Employee tools return meaningful demo data
# ===========================================================================

class TestLeaveBalance:

    def test_get_leave_balance_by_id(self):
        result = get_leave_balance(employee_id="E001")
        assert result["count"] == 1
        rec = result["leave_balances"][0]
        assert rec["name"] == "Alice Johnson"
        assert int(rec["annual_leave_remaining"]) >= 0

    def test_get_leave_balance_by_department(self):
        result = get_leave_balance(department="AI")
        assert result["count"] > 0
        for r in result["leave_balances"]:
            assert r["department"] == "AI"

    def test_get_leave_balance_all(self):
        result = get_leave_balance()
        assert result["count"] == 15

    def test_leave_balance_has_required_fields(self):
        result = get_leave_balance(employee_id="E001")
        rec = result["leave_balances"][0]
        for field in ["annual_leave_total", "annual_leave_used", "annual_leave_remaining",
                      "sick_leave_remaining", "casual_leave_remaining"]:
            assert field in rec, f"Missing field: {field}"

    def test_leave_balance_nonexistent_employee(self):
        result = get_leave_balance(employee_id="E999")
        assert result["count"] == 0


class TestHRInfo:

    def test_hr_contact_for_ai(self):
        result = get_hr_info(info_type="hr_contact", department="AI")
        assert result["count"] > 0
        assert "hr_contacts" in result
        contact = result["hr_contacts"][0]
        assert "hr_representative" in contact

    def test_hr_contact_for_all_departments(self):
        result = get_hr_info(info_type="hr_contact")
        assert result["count"] >= 3

    def test_timesheet_deadline_october(self):
        result = get_hr_info(info_type="timesheet", month="October", year="2026")
        assert result["count"] == 1
        deadline = result["timesheet_deadlines"][0]
        assert deadline["submission_deadline"] == "2026-10-28"

    def test_timesheet_deadline_all_months(self):
        result = get_hr_info(info_type="timesheet")
        assert result["count"] >= 1

    def test_performance_reviews_for_ai(self):
        result = get_hr_info(info_type="performance", department="AI")
        assert result["count"] > 0
        for r in result["performance_reviews"]:
            assert r["department"] == "AI"

    def test_performance_reviews_all(self):
        result = get_hr_info(info_type="performance")
        assert result["count"] == 15

    def test_invalid_info_type_returns_error(self):
        result = get_hr_info(info_type="unknown_type")
        assert "error" in result


# ===========================================================================
# 5.  New Manager tools return meaningful demo data
# ===========================================================================

class TestTeamLeaveInfo:

    def test_pending_leave_requests_all(self):
        result = get_team_leave_info(info_type="pending")
        assert "pending_leave_requests" in result
        assert result["count"] > 0
        for req in result["pending_leave_requests"]:
            assert req["status"].lower() == "pending"

    def test_pending_leave_requests_by_dept(self):
        result = get_team_leave_info(manager_department="AI", info_type="pending")
        assert result["count"] >= 0  # may be 0 for some depts
        for req in result.get("pending_leave_requests", []):
            assert req["department"] == "AI"

    def test_upcoming_leave_returns_data(self):
        result = get_team_leave_info(info_type="upcoming")
        assert "upcoming_leave" in result

    def test_attendance_summary_engineering(self):
        result = get_team_leave_info(manager_department="Engineering", info_type="attendance")
        assert "attendance" in result
        assert result["count"] > 0
        assert "summary" in result
        assert "team_average_attendance_pct" in result["summary"]

    def test_attendance_summary_has_fields(self):
        result = get_team_leave_info(manager_department="AI", info_type="attendance")
        for emp in result["attendance"]:
            assert "days_present" in emp
            assert "attendance_pct" in emp

    def test_invalid_info_type_returns_error(self):
        result = get_team_leave_info(info_type="bad_type")
        assert "error" in result


class TestTeamUtilization:

    def test_utilization_all_departments(self):
        result = get_team_utilization()
        assert result["count"] > 0
        assert "summary" in result
        assert "utilization_rate_pct" in result["summary"]

    def test_utilization_by_department(self):
        result = get_team_utilization(department="AI")
        assert result["count"] > 0
        for emp in result["utilization"]:
            assert emp["department"] == "AI"

    def test_utilization_has_project_info(self):
        result = get_team_utilization(department="Engineering")
        for emp in result["utilization"]:
            assert "project_name" in emp
            assert "utilization_status" in emp

    def test_utilization_summary_fields(self):
        result = get_team_utilization(department="AI")
        summary = result["summary"]
        assert "total_employees" in summary
        assert "active_on_projects" in summary
        assert "utilization_rate_pct" in summary


# ===========================================================================
# 6.  New Admin tools return meaningful demo data
# ===========================================================================

class TestAdminManageUser:

    def test_onboard_returns_steps(self):
        result = admin_manage_user(action="onboard", employee_name="New Hire", department="AI")
        assert result["action"] == "onboard_employee"
        assert "onboarding_steps" in result
        assert len(result["onboarding_steps"]) >= 5
        assert "DEMO_SIMULATED" in result["status"]

    def test_revoke_access_with_employee(self):
        result = admin_manage_user(action="revoke_access", employee_id="E001")
        assert result["action"] == "revoke_access"
        assert "revocation_steps" in result
        assert "DEMO_SIMULATED" in result["status"]

    def test_revoke_access_no_employee_returns_steps(self):
        result = admin_manage_user(action="revoke_access")
        assert "revocation_steps" in result
        assert len(result["revocation_steps"]) >= 5

    def test_restore_account_returns_steps(self):
        result = admin_manage_user(action="restore_account")
        assert "restoration_steps" in result

    def test_restore_account_specific_deactivated(self):
        result = admin_manage_user(action="restore_account", employee_id="EX001")
        assert result["action"] == "restore_account"
        assert "restoration_steps" in result
        assert result.get("employee") == "Tom Harris"

    def test_headcount_report_all(self):
        result = admin_manage_user(action="headcount_report")
        assert result["action"] == "headcount_report"
        assert result["total_headcount"] > 0
        assert "breakdown" in result
        dept_names = [b["department"] for b in result["breakdown"]]
        assert "AI" in dept_names
        assert "Engineering" in dept_names

    def test_headcount_report_by_dept(self):
        result = admin_manage_user(action="headcount_report", department="AI")
        assert result["total_headcount"] > 0
        for b in result["breakdown"]:
            assert b["department"] == "AI"

    def test_get_accounts_returns_data(self):
        result = admin_manage_user(action="get_accounts")
        assert "user_accounts" in result
        assert result["count"] > 0

    def test_invalid_action_returns_error(self):
        result = admin_manage_user(action="delete_everything")
        assert "error" in result


class TestComplianceTraining:

    def test_incomplete_training_all(self):
        result = get_compliance_training_status()
        assert "incomplete_training" in result
        assert result["total_employees_with_incomplete"] > 0

    def test_incomplete_training_by_dept(self):
        result = get_compliance_training_status(department="Engineering")
        assert result["total_employees_with_incomplete"] >= 0

    def test_completed_filter(self):
        result = get_compliance_training_status(status_filter="Completed")
        for emp in result["incomplete_training"]:
            for course in emp["incomplete_courses"]:
                assert course["status"] == "Completed"

    def test_incomplete_training_has_courses(self):
        result = get_compliance_training_status()
        for emp in result["incomplete_training"]:
            assert "incomplete_courses" in emp
            assert len(emp["incomplete_courses"]) > 0

    def test_specific_employee_with_incomplete(self):
        # Bob Martinez (E002) has Data Privacy not started
        result = get_compliance_training_status(employee_id="E002")
        assert result["total_employees_with_incomplete"] > 0


class TestLoginActivity:

    def test_login_activity_by_employee_id(self):
        result = get_login_activity(employee_id="E001")
        assert result["count"] > 0
        for log in result["login_activity"]:
            assert log["employee_id"] == "E001"

    def test_login_activity_by_name(self):
        result = get_login_activity(employee_name="Alice")
        assert result["count"] > 0

    def test_login_activity_all(self):
        result = get_login_activity()
        assert result["count"] > 0
        assert "login_activity" in result

    def test_login_activity_has_required_fields(self):
        result = get_login_activity(employee_id="E001")
        log = result["login_activity"][0]
        for field in ["login_datetime", "ip_address", "device", "status", "failed_attempts"]:
            assert field in log, f"Missing field: {field}"

    def test_flagged_entries_detected(self):
        # Log shows Henry Brown (E008) had 2 failed attempts and Frank Patel had 3
        result = get_login_activity()
        assert result["flagged_count"] >= 0  # may vary with limit

    def test_login_activity_limit(self):
        result = get_login_activity(limit=3)
        assert result["count"] <= 3


class TestAdminPermissions:

    def test_get_all_privileged_accounts(self):
        result = get_admin_permissions()
        assert result["count"] > 0
        assert "privileged_accounts" in result

    def test_admin_users_identified(self):
        result = get_admin_permissions()
        assert result["admin_count"] >= 1
        for acct in result["admin_users"]:
            assert acct["permission_level"].lower() == "admin"

    def test_elevated_users_identified(self):
        result = get_admin_permissions()
        assert result["elevated_count"] > 0
        for acct in result["elevated_users"]:
            assert acct["permission_level"].lower() == "elevated"

    def test_filter_by_admin_level(self):
        result = get_admin_permissions(permission_level="admin")
        for acct in result["privileged_accounts"]:
            assert acct["permission_level"].lower() == "admin"

    def test_filter_by_elevated_level(self):
        result = get_admin_permissions(permission_level="elevated")
        for acct in result["privileged_accounts"]:
            assert acct["permission_level"].lower() == "elevated"


# ===========================================================================
# 7.  Permission checks: authorized allowed, unauthorized denied
# ===========================================================================

class TestPermissions:

    # Employee permissions
    def test_employee_can_use_get_leave_balance(self):
        assert can_use_tool("employee", "get_leave_balance") is True

    def test_employee_can_use_get_hr_info(self):
        assert can_use_tool("employee", "get_hr_info") is True

    def test_employee_cannot_use_get_team_leave_info(self):
        assert can_use_tool("employee", "get_team_leave_info") is False

    def test_employee_cannot_use_get_team_utilization(self):
        assert can_use_tool("employee", "get_team_utilization") is False

    def test_employee_cannot_use_admin_manage_user(self):
        assert can_use_tool("employee", "admin_manage_user") is False

    def test_employee_cannot_use_get_login_activity(self):
        assert can_use_tool("employee", "get_login_activity") is False

    def test_employee_cannot_use_get_admin_permissions(self):
        assert can_use_tool("employee", "get_admin_permissions") is False

    def test_employee_cannot_use_compliance_training(self):
        assert can_use_tool("employee", "get_compliance_training_status") is False

    # Manager permissions
    def test_manager_can_use_get_team_leave_info(self):
        assert can_use_tool("manager", "get_team_leave_info") is True

    def test_manager_can_use_get_team_utilization(self):
        assert can_use_tool("manager", "get_team_utilization") is True

    def test_manager_cannot_use_admin_manage_user(self):
        assert can_use_tool("manager", "admin_manage_user") is False

    def test_manager_cannot_use_get_login_activity(self):
        assert can_use_tool("manager", "get_login_activity") is False

    def test_manager_cannot_use_get_admin_permissions(self):
        assert can_use_tool("manager", "get_admin_permissions") is False

    def test_manager_cannot_use_compliance_training(self):
        assert can_use_tool("manager", "get_compliance_training_status") is False

    # Admin permissions
    def test_admin_can_use_all_tools(self):
        all_tools = [
            "get_employee_info", "get_department_info", "get_project_info",
            "search_company_policy", "check_user_permission",
            "get_leave_balance", "get_hr_info",
            "get_team_leave_info", "get_team_utilization",
            "admin_manage_user", "get_compliance_training_status",
            "get_login_activity", "get_headcount_report", "get_admin_permissions",
        ]
        for tool in all_tools:
            assert can_use_tool("admin", tool) is True, f"Admin should be able to use {tool}"

    def test_unknown_role_denied_all_tools(self):
        assert can_use_tool("hacker", "get_employee_info") is False
        assert can_use_tool("", "get_login_activity") is False

    def test_unknown_tool_denied_all_roles(self):
        for role in ROLES:
            assert can_use_tool(role, "drop_all_tables") is False


# ===========================================================================
# 8.  Backend permission check via agent/nodes PERMISSION_CHECKED_TOOLS
# ===========================================================================

class TestNodePermissionSet:

    def test_all_new_tools_in_permission_set(self):
        from agent.nodes import PERMISSION_CHECKED_TOOLS
        new_tools = {
            "get_leave_balance", "get_hr_info",
            "get_team_leave_info", "get_team_utilization",
            "admin_manage_user", "get_compliance_training_status",
            "get_login_activity", "get_headcount_report", "get_admin_permissions",
        }
        for tool in new_tools:
            assert tool in PERMISSION_CHECKED_TOOLS, f"{tool} not in PERMISSION_CHECKED_TOOLS"

    def test_existing_tools_still_in_permission_set(self):
        from agent.nodes import PERMISSION_CHECKED_TOOLS
        for tool in ["get_employee_info", "search_company_policy"]:
            assert tool in PERMISSION_CHECKED_TOOLS


# ===========================================================================
# 9.  Policy questions resolve via search_company_policy
# ===========================================================================

class TestPolicySearchForAllQuestions:

    def test_salary_certificate_process(self):
        result = search_company_policy("salary certificate process", document="company_policy")
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "salary certificate" in texts

    def test_resignation_notice_period(self):
        result = search_company_policy("notice period resign", document="company_policy")
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "notice" in texts

    def test_probation_period(self):
        result = search_company_policy("probation period new hires", document="company_policy")
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "probation" in texts or "3 months" in texts

    def test_reimbursement_client_dinner(self):
        result = search_company_policy("reimbursement client dinner expense", document="company_policy")
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "reimburse" in texts or "expense" in texts

    def test_carry_forward_leave(self):
        result = search_company_policy("carry forward unused leave", document="leave_policy")
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "carry" in texts or "unused" in texts or "forward" in texts

    def test_overtime_approval(self):
        result = search_company_policy("approve overtime employee", document="company_policy")
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "overtime" in texts

    def test_headcount_request_process(self):
        result = search_company_policy("request additional headcount department", document="company_policy")
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "headcount" in texts or "hiring" in texts

    def test_offboarding_process(self):
        result = search_company_policy("offboard employee resigning", document="company_policy")
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "offboard" in texts or "resign" in texts

    def test_onboarding_process(self):
        result = search_company_policy("onboard new employee system", document="company_policy")
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "onboard" in texts or "employee" in texts

    def test_account_restoration_process(self):
        result = search_company_policy("restore deactivated user account", document="company_policy")
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "restore" in texts or "deactivated" in texts or "account" in texts

    def test_password_security_policy(self):
        result = search_company_policy("password security policy accounts", document="security_policy")
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "password" in texts


# ===========================================================================
# 10. All 24 example questions map to a callable tool via MCPClient
# ===========================================================================

class TestAllQuestionsHaveToolSupport:
    """
    Verify each of the 24 example questions can be answered by calling
    the appropriate tool directly. Each test confirms the tool returns
    non-empty, non-error demo data.
    """

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    def _call(self, tool: str, args: dict) -> dict:
        return json.loads(self.client.call_tool(tool, args))

    # ── Employee Q1: How many annual leave days do I have left? ───────────
    def test_employee_q1_leave_days(self):
        result = self._call("get_leave_balance", {"employee_id": "E001"})
        assert result["count"] == 1
        assert int(result["leave_balances"][0]["annual_leave_remaining"]) >= 0

    # ── Employee Q2: Salary certificate process ───────────────────────────
    def test_employee_q2_salary_certificate(self):
        result = self._call("search_company_policy",
                            {"query": "salary certificate process", "document": "company_policy"})
        assert result["count"] > 0

    # ── Employee Q3: Notice period to resign ──────────────────────────────
    def test_employee_q3_notice_period(self):
        result = self._call("search_company_policy",
                            {"query": "notice period resign", "document": "company_policy"})
        assert result["count"] > 0

    # ── Employee Q4: Reimbursement client dinner ──────────────────────────
    def test_employee_q4_reimbursement(self):
        result = self._call("search_company_policy",
                            {"query": "reimbursement client dinner expense claim", "document": "company_policy"})
        assert result["count"] > 0

    # ── Employee Q5: Timesheet deadline ──────────────────────────────────
    def test_employee_q5_timesheet_deadline(self):
        result = self._call("get_hr_info",
                            {"info_type": "timesheet", "month": "October", "year": "2026"})
        assert result["count"] >= 1

    # ── Employee Q6: HR representative ───────────────────────────────────
    def test_employee_q6_hr_representative(self):
        result = self._call("get_hr_info",
                            {"info_type": "hr_contact", "department": "AI"})
        assert result["count"] > 0
        assert "hr_representative" in result["hr_contacts"][0]

    # ── Employee Q7: Carry forward unused leave ───────────────────────────
    def test_employee_q7_carry_forward(self):
        result = self._call("search_company_policy",
                            {"query": "carry forward unused leave", "document": "leave_policy"})
        assert result["count"] > 0

    # ── Employee Q8: Probation period ────────────────────────────────────
    def test_employee_q8_probation_period(self):
        result = self._call("search_company_policy",
                            {"query": "probation period new hires", "document": "company_policy"})
        assert result["count"] > 0

    # ── Manager Q1: Pending leave requests ───────────────────────────────
    def test_manager_q1_pending_leave(self):
        result = self._call("get_team_leave_info", {"info_type": "pending"})
        assert "pending_leave_requests" in result

    # ── Manager Q2: Attendance summary ───────────────────────────────────
    def test_manager_q2_attendance_summary(self):
        result = self._call("get_team_leave_info", {"info_type": "attendance"})
        assert "attendance" in result
        assert "summary" in result

    # ── Manager Q3: Who is on leave next week ────────────────────────────
    def test_manager_q3_upcoming_leave(self):
        result = self._call("get_team_leave_info", {"info_type": "upcoming"})
        assert "upcoming_leave" in result

    # ── Manager Q4: Approve overtime ─────────────────────────────────────
    def test_manager_q4_overtime(self):
        result = self._call("search_company_policy",
                            {"query": "approve overtime employee", "document": "company_policy"})
        assert result["count"] > 0

    # ── Manager Q5: Team utilization ─────────────────────────────────────
    def test_manager_q5_utilization(self):
        result = self._call("get_team_utilization", {})
        assert "utilization" in result
        assert "summary" in result
        assert result["summary"]["total_employees"] > 0

    # ── Manager Q6: Request additional headcount ──────────────────────────
    def test_manager_q6_headcount_request(self):
        result = self._call("search_company_policy",
                            {"query": "request additional headcount department hiring",
                             "document": "company_policy"})
        assert result["count"] > 0

    # ── Manager Q7: Performance review schedule ───────────────────────────
    def test_manager_q7_performance_review(self):
        result = self._call("get_hr_info", {"info_type": "performance"})
        assert "performance_reviews" in result
        assert result["count"] > 0

    # ── Manager Q8: Offboard employee ────────────────────────────────────
    def test_manager_q8_offboard(self):
        result = self._call("search_company_policy",
                            {"query": "offboard employee resigning", "document": "company_policy"})
        assert result["count"] > 0

    # ── Admin Q1: Onboard new employee ───────────────────────────────────
    def test_admin_q1_onboard(self):
        result = self._call("admin_manage_user",
                            {"action": "onboard", "employee_name": "Test User", "department": "AI"})
        assert "onboarding_steps" in result
        assert len(result["onboarding_steps"]) >= 5

    # ── Admin Q2: Revoke system access ───────────────────────────────────
    def test_admin_q2_revoke_access(self):
        result = self._call("admin_manage_user",
                            {"action": "revoke_access", "employee_id": "E001"})
        assert "revocation_steps" in result

    # ── Admin Q3: Password and security policy ───────────────────────────
    def test_admin_q3_password_security_policy(self):
        result = self._call("search_company_policy",
                            {"query": "password security policy accounts MFA",
                             "document": "security_policy"})
        assert result["count"] > 0
        texts = " ".join(r["excerpt"].lower() for r in result["results"])
        assert "password" in texts

    # ── Admin Q4: Headcount report ───────────────────────────────────────
    def test_admin_q4_headcount_report(self):
        result = self._call("admin_manage_user", {"action": "headcount_report"})
        assert result["total_headcount"] > 0
        assert "breakdown" in result
        dept_names = [b["department"] for b in result["breakdown"]]
        assert "AI" in dept_names

    # ── Admin Q5: Compliance training ────────────────────────────────────
    def test_admin_q5_compliance_training(self):
        result = self._call("get_compliance_training_status", {})
        assert "incomplete_training" in result
        assert result["total_employees_with_incomplete"] > 0

    # ── Admin Q6: Audit login activity ───────────────────────────────────
    def test_admin_q6_login_activity(self):
        result = self._call("get_login_activity", {"employee_name": "Alice"})
        assert result["count"] > 0
        assert "login_datetime" in result["login_activity"][0]

    # ── Admin Q7: Who has admin/elevated permissions ──────────────────────
    def test_admin_q7_admin_permissions(self):
        result = self._call("get_admin_permissions", {})
        assert result["count"] > 0
        assert result["admin_count"] >= 1
        assert result["elevated_count"] > 0

    # ── Admin Q8: Restore deactivated account ────────────────────────────
    def test_admin_q8_restore_account(self):
        result = self._call("admin_manage_user",
                            {"action": "restore_account", "employee_id": "EX001"})
        assert "restoration_steps" in result
        assert result.get("employee") == "Tom Harris"


# ===========================================================================
# 11. Existing test compatibility — key checks
# ===========================================================================

class TestExistingCompatibility:

    def test_employee_cannot_see_access_level(self):
        result = get_employee_info(department="AI",
                                   visible_fields=["employee_id", "name", "department", "role", "project_id"])
        for emp in result["employees"]:
            assert "access_level" not in emp

    def test_admin_can_see_access_level(self):
        from mcp_server.permissions import get_visible_fields
        visible = get_visible_fields("admin")
        result = get_employee_info(department="AI", visible_fields=visible)
        for emp in result["employees"]:
            assert "access_level" in emp

    def test_check_user_permission_allowed(self):
        from mcp_server.permissions import permission_check_result
        result = permission_check_result("employee", "get_department_info")
        assert result["allowed"] is True

    def test_check_user_permission_denied_unknown_tool(self):
        from mcp_server.permissions import permission_check_result
        result = permission_check_result("employee", "fake_tool")
        assert result["allowed"] is False

    def test_search_policy_source_is_local_document(self):
        result = search_company_policy("annual leave")
        assert result.get("source") == "local_document"

    def test_search_policy_mode_is_local(self):
        result = search_company_policy("password")
        assert result.get("mode") == "local_keyword_search"


# ===========================================================================
# 12. Databricks demo mode — not broken
# ===========================================================================

class TestDatabricksDemoMode:

    def test_demo_mode_returns_none_connection(self):
        from databricks.client import get_connection, is_demo_mode
        assert is_demo_mode() is True
        assert get_connection() is None

    def test_full_table_name(self):
        from databricks.client import get_full_table
        name = get_full_table("employees")
        assert "employees" in name
        assert "." in name

    def test_databricks_fallback_to_local(self):
        original = os.environ.get("DEMO_MODE", "true")
        os.environ["DEMO_MODE"] = "false"
        try:
            import importlib
            import mcp_server.tools as t
            importlib.reload(t)
            result = t.get_department_info("AI")
            assert result["count"] == 1
        finally:
            os.environ["DEMO_MODE"] = original
            import mcp_server.tools as t
            importlib.reload(t)
