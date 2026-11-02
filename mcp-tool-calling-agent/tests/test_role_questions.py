"""
tests/test_role_questions.py
-----------------------------
Tests for the role-based example question filtering system.

Verifies (matching the 14 requirements in the specification):
 1.  Employee returns exactly 10 Employee questions (IT support).
 2.  Manager returns exactly 10 Manager questions (IT support).
 3.  Admin returns exactly 10 Admin questions (IT support).
 4.  Employee list contains no Manager questions.
 5.  Employee list contains no Admin questions.
 6.  Manager list contains no Employee questions.
 7.  Manager list contains no Admin questions.
 8.  Admin list contains no Employee questions.
 9.  Admin list contains no Manager questions.
10.  Changing the selected role changes the displayed question list.
11.  Existing backend permission tests still pass (verified by running
     the suite; this module also re-checks the key invariants directly).
12.  Existing MCP tool tests still pass (independent suite).
13.  Existing agent tests still pass (independent suite).
14.  Existing policy search tests still pass (independent suite).

Run: pytest tests/test_role_questions.py -v
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATA_DIR", "data")
os.environ.setdefault("DOCUMENTS_DIR", "documents")

from role_questions import (
    get_questions_for_role,
    get_all_roles,
    get_catalogue,
    ROLE_EXAMPLE_QUESTIONS,
)
from mcp_server.permissions import can_use_tool, ROLE_PERMISSIONS


# ---------------------------------------------------------------------------
# Expected canonical question lists (exactly as specified)
# ---------------------------------------------------------------------------

EXPECTED_EMPLOYEE_QUESTIONS: list[str] = [
    "Is there currently an IT incident affecting the application I'm trying to use?",
    "Is the company VPN currently experiencing any issues?",
    "Are there any network problems affecting my office right now?",
    "Why can't I access the internal application?",
    "Is my login/authentication problem a known issue?",
    "What is the current status of my open IT ticket?",
    "Has someone from IT been assigned to my ticket?",
    "When was my IT ticket last updated?",
    "Is there already an incident for the problem I'm experiencing?",
    "Can you create an IT ticket for my issue if it hasn't already been reported?",
]

EXPECTED_MANAGER_QUESTIONS: list[str] = [
    "Are any members of my team currently affected by an IT incident?",
    "How many people on my team are affected by the current issue?",
    "Is this problem limited to my team, or is it affecting other teams too?",
    "What is the current status of the incident affecting my team?",
    "Who is currently handling the incident?",
    "When was the incident first reported and when was it last updated?",
    "Is there an estimated time for resolving the issue?",
    "Which members of my team currently have unresolved IT tickets?",
    "Are there any recurring IT problems affecting my team?",
    "Can you escalate the issue if it is blocking my team's work?",
]

EXPECTED_ADMIN_QUESTIONS: list[str] = [
    "What are the currently active IT incidents across the company?",
    "Which critical applications or services are currently unavailable?",
    "Which offices or departments are currently affected by network issues?",
    "How many users are currently affected by each major incident?",
    "What is the current status and latest update for each major incident?",
    "Which team is responsible for resolving each active incident?",
    "Which incidents have been open longer than their SLA?",
    "Which systems have had recurring incidents recently?",
    "Are there duplicate incidents for the same underlying problem?",
    "Which active issues require escalation or immediate attention?",
]


# ===========================================================================
# Requirement 1 – Employee returns exactly 8 Employee questions
# ===========================================================================

class TestEmployeeQuestions:

    def test_employee_returns_exactly_10_questions(self):
        """Requirement 1: Employee returns exactly 10 IT support questions."""
        qs = get_questions_for_role("employee")
        assert len(qs) == 10, f"Expected 10, got {len(qs)}: {qs}"

    def test_employee_returns_exact_question_content(self):
        """All 10 exact Employee questions must be present."""
        qs = get_questions_for_role("employee")
        for expected in EXPECTED_EMPLOYEE_QUESTIONS:
            assert expected in qs, f"Missing employee question: {expected!r}"

    def test_employee_returns_list_type(self):
        assert isinstance(get_questions_for_role("employee"), list)

    def test_employee_questions_are_all_strings(self):
        for q in get_questions_for_role("employee"):
            assert isinstance(q, str) and len(q) > 0


# ===========================================================================
# Requirement 2 – Manager returns exactly 8 Manager questions
# ===========================================================================

class TestManagerQuestions:

    def test_manager_returns_exactly_10_questions(self):
        """Requirement 2: Manager returns exactly 10 IT support questions."""
        qs = get_questions_for_role("manager")
        assert len(qs) == 10, f"Expected 10, got {len(qs)}: {qs}"

    def test_manager_returns_exact_question_content(self):
        """All 10 exact Manager questions must be present."""
        qs = get_questions_for_role("manager")
        for expected in EXPECTED_MANAGER_QUESTIONS:
            assert expected in qs, f"Missing manager question: {expected!r}"

    def test_manager_returns_list_type(self):
        assert isinstance(get_questions_for_role("manager"), list)

    def test_manager_questions_are_all_strings(self):
        for q in get_questions_for_role("manager"):
            assert isinstance(q, str) and len(q) > 0


# ===========================================================================
# Requirement 3 – Admin returns exactly 8 Admin questions
# ===========================================================================

class TestAdminQuestions:

    def test_admin_returns_exactly_10_questions(self):
        """Requirement 3: Admin returns exactly 10 IT support questions."""
        qs = get_questions_for_role("admin")
        assert len(qs) == 10, f"Expected 10, got {len(qs)}: {qs}"

    def test_admin_returns_exact_question_content(self):
        """All 10 exact Admin questions must be present."""
        qs = get_questions_for_role("admin")
        for expected in EXPECTED_ADMIN_QUESTIONS:
            assert expected in qs, f"Missing admin question: {expected!r}"

    def test_admin_returns_list_type(self):
        assert isinstance(get_questions_for_role("admin"), list)

    def test_admin_questions_are_all_strings(self):
        for q in get_questions_for_role("admin"):
            assert isinstance(q, str) and len(q) > 0


# ===========================================================================
# Requirements 4 & 5 – Employee list contains NO Manager or Admin questions
# ===========================================================================

class TestEmployeeExclusion:

    def test_employee_contains_no_manager_questions(self):
        """Requirement 4: Employee list contains no Manager questions."""
        emp_qs = set(get_questions_for_role("employee"))
        for q in EXPECTED_MANAGER_QUESTIONS:
            assert q not in emp_qs, (
                f"Manager question found in Employee list: {q!r}"
            )

    def test_employee_contains_no_admin_questions(self):
        """Requirement 5: Employee list contains no Admin questions."""
        emp_qs = set(get_questions_for_role("employee"))
        for q in EXPECTED_ADMIN_QUESTIONS:
            assert q not in emp_qs, (
                f"Admin question found in Employee list: {q!r}"
            )

    def test_employee_set_is_disjoint_from_manager(self):
        emp_qs = set(get_questions_for_role("employee"))
        mgr_qs = set(get_questions_for_role("manager"))
        overlap = emp_qs & mgr_qs
        assert overlap == set(), f"Overlap between employee and manager: {overlap}"

    def test_employee_set_is_disjoint_from_admin(self):
        emp_qs = set(get_questions_for_role("employee"))
        adm_qs = set(get_questions_for_role("admin"))
        overlap = emp_qs & adm_qs
        assert overlap == set(), f"Overlap between employee and admin: {overlap}"


# ===========================================================================
# Requirements 6 & 7 – Manager list contains NO Employee or Admin questions
# ===========================================================================

class TestManagerExclusion:

    def test_manager_contains_no_employee_questions(self):
        """Requirement 6: Manager list contains no Employee questions."""
        mgr_qs = set(get_questions_for_role("manager"))
        for q in EXPECTED_EMPLOYEE_QUESTIONS:
            assert q not in mgr_qs, (
                f"Employee question found in Manager list: {q!r}"
            )

    def test_manager_contains_no_admin_questions(self):
        """Requirement 7: Manager list contains no Admin questions."""
        mgr_qs = set(get_questions_for_role("manager"))
        for q in EXPECTED_ADMIN_QUESTIONS:
            assert q not in mgr_qs, (
                f"Admin question found in Manager list: {q!r}"
            )

    def test_manager_set_is_disjoint_from_employee(self):
        mgr_qs = set(get_questions_for_role("manager"))
        emp_qs = set(get_questions_for_role("employee"))
        overlap = mgr_qs & emp_qs
        assert overlap == set(), f"Overlap between manager and employee: {overlap}"

    def test_manager_set_is_disjoint_from_admin(self):
        mgr_qs = set(get_questions_for_role("manager"))
        adm_qs = set(get_questions_for_role("admin"))
        overlap = mgr_qs & adm_qs
        assert overlap == set(), f"Overlap between manager and admin: {overlap}"


# ===========================================================================
# Requirements 8 & 9 – Admin list contains NO Employee or Manager questions
# ===========================================================================

class TestAdminExclusion:

    def test_admin_contains_no_employee_questions(self):
        """Requirement 8: Admin list contains no Employee questions."""
        adm_qs = set(get_questions_for_role("admin"))
        for q in EXPECTED_EMPLOYEE_QUESTIONS:
            assert q not in adm_qs, (
                f"Employee question found in Admin list: {q!r}"
            )

    def test_admin_contains_no_manager_questions(self):
        """Requirement 9: Admin list contains no Manager questions."""
        adm_qs = set(get_questions_for_role("admin"))
        for q in EXPECTED_MANAGER_QUESTIONS:
            assert q not in adm_qs, (
                f"Manager question found in Admin list: {q!r}"
            )

    def test_admin_set_is_disjoint_from_employee(self):
        adm_qs = set(get_questions_for_role("admin"))
        emp_qs = set(get_questions_for_role("employee"))
        overlap = adm_qs & emp_qs
        assert overlap == set(), f"Overlap between admin and employee: {overlap}"

    def test_admin_set_is_disjoint_from_manager(self):
        adm_qs = set(get_questions_for_role("admin"))
        mgr_qs = set(get_questions_for_role("manager"))
        overlap = adm_qs & mgr_qs
        assert overlap == set(), f"Overlap between admin and manager: {overlap}"


# ===========================================================================
# Requirement 10 – Changing role changes the displayed question list
# ===========================================================================

class TestRoleChangesQuestions:

    def test_employee_and_manager_lists_differ(self):
        """Requirement 10: Changing role from employee to manager changes questions."""
        emp_qs = get_questions_for_role("employee")
        mgr_qs = get_questions_for_role("manager")
        assert emp_qs != mgr_qs, "employee and manager should have different question sets"

    def test_manager_and_admin_lists_differ(self):
        """Requirement 10: Changing role from manager to admin changes questions."""
        mgr_qs = get_questions_for_role("manager")
        adm_qs = get_questions_for_role("admin")
        assert mgr_qs != adm_qs, "manager and admin should have different question sets"

    def test_employee_and_admin_lists_differ(self):
        """Requirement 10: Changing role from employee to admin changes questions."""
        emp_qs = get_questions_for_role("employee")
        adm_qs = get_questions_for_role("admin")
        assert emp_qs != adm_qs, "employee and admin should have different question sets"

    def test_all_three_role_lists_are_distinct(self):
        emp_qs = set(get_questions_for_role("employee"))
        mgr_qs = set(get_questions_for_role("manager"))
        adm_qs = set(get_questions_for_role("admin"))
        assert emp_qs != mgr_qs
        assert mgr_qs != adm_qs
        assert emp_qs != adm_qs

    def test_simulated_role_change_employee_to_manager(self):
        """Simulate what Streamlit does on selectbox change: re-run with new role."""
        first_result = get_questions_for_role("employee")
        second_result = get_questions_for_role("manager")
        assert first_result != second_result

    def test_simulated_role_change_manager_to_admin(self):
        first_result = get_questions_for_role("manager")
        second_result = get_questions_for_role("admin")
        assert first_result != second_result

    def test_simulated_role_change_admin_to_employee(self):
        first_result = get_questions_for_role("admin")
        second_result = get_questions_for_role("employee")
        assert first_result != second_result


# ===========================================================================
# Requirement 11 – Backend permission checks remain active
# ===========================================================================

class TestBackendPermissionStillEnforced:
    """
    Requirement 11: Existing backend permission tests still pass.
    Verify that the UI-level question change did NOT alter permissions.
    """

    def test_employee_tool_permissions_contain_core_tools(self):
        """Employee ROLE_PERMISSIONS must still contain all original core tools."""
        required = {
            "get_department_info",
            "get_project_info",
            "get_employee_info",
            "search_company_policy",
            "check_user_permission",
        }
        assert required.issubset(set(ROLE_PERMISSIONS["employee"]))

    def test_manager_tool_permissions_contain_core_tools(self):
        required = {
            "get_department_info",
            "get_project_info",
            "get_employee_info",
            "search_company_policy",
            "check_user_permission",
        }
        assert required.issubset(set(ROLE_PERMISSIONS["manager"]))

    def test_admin_tool_permissions_contain_core_tools(self):
        required = {
            "get_department_info",
            "get_project_info",
            "get_employee_info",
            "search_company_policy",
            "check_user_permission",
        }
        assert required.issubset(set(ROLE_PERMISSIONS["admin"]))

    def test_unknown_tool_denied_for_all_roles(self):
        for role in get_all_roles():
            assert can_use_tool(role, "drop_all_tables") is False

    def test_backend_still_denies_unknown_role(self):
        assert can_use_tool("attacker", "get_employee_info") is False
        assert can_use_tool("", "get_employee_info") is False

    def test_employee_denied_unknown_tools_via_backend(self):
        assert can_use_tool("employee", "delete_record") is False
        assert can_use_tool("employee", "get_salary_data") is False

    def test_tool_node_permission_set_intact(self):
        from agent.nodes import PERMISSION_CHECKED_TOOLS
        assert len(PERMISSION_CHECKED_TOOLS) > 0
        assert "get_employee_info" in PERMISSION_CHECKED_TOOLS
        assert "search_company_policy" in PERMISSION_CHECKED_TOOLS

    def test_ui_hiding_does_not_grant_backend_access(self):
        """
        An admin-specific UI question being hidden from employee does NOT
        mean the employee bypasses the backend check.
        The backend must still deny any unknown/restricted tool.
        """
        # The employee cannot call a tool that doesn't exist
        assert can_use_tool("employee", "audit_login_activity") is False
        assert can_use_tool("employee", "revoke_system_access") is False


# ===========================================================================
# Invalid / edge-case role handling
# ===========================================================================

class TestInvalidRoleHandling:

    def test_unknown_role_returns_empty_list(self):
        assert get_questions_for_role("hacker") == []

    def test_empty_string_returns_empty_list(self):
        assert get_questions_for_role("") == []

    def test_whitespace_only_returns_empty_list(self):
        assert get_questions_for_role("   ") == []

    def test_none_like_string_returns_empty_list(self):
        assert get_questions_for_role("None") == []

    def test_case_insensitive_employee(self):
        lower = get_questions_for_role("employee")
        upper = get_questions_for_role("EMPLOYEE")
        mixed = get_questions_for_role("Employee")
        assert lower == upper == mixed

    def test_case_insensitive_manager(self):
        lower = get_questions_for_role("manager")
        upper = get_questions_for_role("MANAGER")
        mixed = get_questions_for_role("Manager")
        assert lower == upper == mixed

    def test_case_insensitive_admin(self):
        lower = get_questions_for_role("admin")
        upper = get_questions_for_role("ADMIN")
        mixed = get_questions_for_role("Admin")
        assert lower == upper == mixed

    def test_returns_copy_not_reference(self):
        """Modifying the returned list must not affect future calls."""
        qs1 = get_questions_for_role("employee")
        qs1.clear()
        qs2 = get_questions_for_role("employee")
        assert len(qs2) == 10


# ===========================================================================
# Mapping integrity
# ===========================================================================

class TestMappingIntegrity:

    def test_all_three_roles_present_in_mapping(self):
        for role in ["employee", "manager", "admin"]:
            assert role in ROLE_EXAMPLE_QUESTIONS

    def test_each_role_has_expected_question_count(self):
        expected_counts = {"employee": 10, "manager": 10, "admin": 10}
        for role, expected in expected_counts.items():
            questions = ROLE_EXAMPLE_QUESTIONS[role]
            assert len(questions) == expected, (
                f"Role '{role}' has {len(questions)} questions, expected {expected}"
            )

    def test_no_duplicate_questions_within_any_role(self):
        for role, questions in ROLE_EXAMPLE_QUESTIONS.items():
            assert len(questions) == len(set(questions)), (
                f"Duplicate questions found for role '{role}'"
            )

    def test_no_duplicate_questions_across_all_roles(self):
        all_qs = []
        for questions in ROLE_EXAMPLE_QUESTIONS.values():
            all_qs.extend(questions)
        assert len(all_qs) == len(set(all_qs)), "Duplicate questions found across roles"

    def test_total_question_count_is_30(self):
        total = sum(len(qs) for qs in ROLE_EXAMPLE_QUESTIONS.values())
        assert total == 30, f"Expected 30 total questions (10 + 10 + 10), got {total}"

    def test_all_questions_are_non_empty_strings(self):
        for role, questions in ROLE_EXAMPLE_QUESTIONS.items():
            for q in questions:
                assert isinstance(q, str) and q.strip(), (
                    f"Empty/non-string question in role '{role}': {q!r}"
                )

    def test_get_all_roles_matches_permissions(self):
        from mcp_server.permissions import ROLES
        assert set(get_all_roles()) == set(ROLES)

    def test_catalogue_helper_returns_30_entries(self):
        assert len(get_catalogue()) == 30

    def test_catalogue_each_entry_has_one_role(self):
        for entry in get_catalogue():
            assert "roles" in entry
            assert len(entry["roles"]) == 1, (
                f"Catalogue entry should have exactly one role: {entry}"
            )

    def test_catalogue_has_question_field(self):
        for entry in get_catalogue():
            assert "question" in entry and entry["question"]


# ===========================================================================
# Exact content spot-checks per role
# ===========================================================================

class TestExactQuestionContent:

    # Employee spot-checks (IT support questions)
    def test_employee_q1(self):
        assert "Is there currently an IT incident affecting the application I'm trying to use?" in get_questions_for_role("employee")

    def test_employee_q4(self):
        assert "Why can't I access the internal application?" in get_questions_for_role("employee")

    def test_employee_q8(self):
        assert "When was my IT ticket last updated?" in get_questions_for_role("employee")

    # Manager spot-checks (IT support questions)
    def test_manager_q1(self):
        assert "Are any members of my team currently affected by an IT incident?" in get_questions_for_role("manager")

    def test_manager_q4(self):
        assert "What is the current status of the incident affecting my team?" in get_questions_for_role("manager")

    def test_manager_q8(self):
        assert "Are there any recurring IT problems affecting my team?" in get_questions_for_role("manager")

    # Admin spot-checks (IT support questions)
    def test_admin_q1(self):
        assert "What are the currently active IT incidents across the company?" in get_questions_for_role("admin")

    def test_admin_q4(self):
        assert "How many users are currently affected by each major incident?" in get_questions_for_role("admin")

    def test_admin_q8(self):
        assert "Which systems have had recurring incidents recently?" in get_questions_for_role("admin")
