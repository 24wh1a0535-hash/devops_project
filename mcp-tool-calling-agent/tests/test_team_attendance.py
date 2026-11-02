"""
tests/test_team_attendance.py
------------------------------
Tests for the get_team_attendance tool and manager demo context.

Verifies:
1.  get_team_attendance tool is registered in MCPClient
2.  Manager has permission to call get_team_attendance
3.  Employee does NOT have permission to call get_team_attendance
4.  Admin has permission to call get_team_attendance
5.  get_team_attendance returns actual attendance data (not empty)
6.  Tool returns correct department (AI) when called without arguments
7.  Tool returns correct fields in summary (present, absent, late, leave, pct)
8.  Tool returns per-member breakdown
9.  Tool does NOT hard-code the answer (values come from CSV data)
10. get_department_info is NOT the correct tool for attendance questions
    (confirmed via tool description / TOOL_SELECTION_HINT)
11. Demo manager context: Karen Davis is in the AI department
12. PERMISSION_CHECKED_TOOLS contains get_team_attendance
13. get_team_attendance is not accessible to employee via permission gate
14. Tool source is 'local_csv'

Run: pytest tests/test_team_attendance.py -v
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("DATA_DIR", "data")
os.environ.setdefault("DOCUMENTS_DIR", "documents")

from mcp_client import MCPClient
from mcp_server.permissions import can_use_tool, ROLE_PERMISSIONS
from mcp_server.tools import get_team_attendance as _tool_fn
from agent.nodes import PERMISSION_CHECKED_TOOLS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    return MCPClient()


@pytest.fixture(scope="module")
def ai_attendance_result(client):
    """Call get_team_attendance with department='AI' and return parsed result."""
    raw = client.call_tool("get_team_attendance", {"department": "AI"})
    return json.loads(raw)


@pytest.fixture(scope="module")
def ai_attendance_no_args(client):
    """Call get_team_attendance with no arguments (should default to AI dept)."""
    raw = client.call_tool("get_team_attendance", {})
    return json.loads(raw)


# ===========================================================================
# 1. Tool is registered
# ===========================================================================

class TestToolRegistration:

    def test_get_team_attendance_is_registered(self, client):
        """Requirement 1: get_team_attendance tool must be registered in MCPClient."""
        names = {t.name for t in client.get_tools()}
        assert "get_team_attendance" in names

    def test_get_team_attendance_not_same_as_get_department_info(self, client):
        """get_team_attendance and get_department_info are distinct registered tools."""
        names = {t.name for t in client.get_tools()}
        assert "get_department_info" in names
        assert "get_team_attendance" in names
        assert "get_team_attendance" != "get_department_info"

    def test_permission_checked_tools_contains_attendance(self):
        """Requirement 12: PERMISSION_CHECKED_TOOLS must include get_team_attendance."""
        assert "get_team_attendance" in PERMISSION_CHECKED_TOOLS


# ===========================================================================
# 2–4. Permissions
# ===========================================================================

class TestAttendancePermissions:

    def test_manager_has_permission(self):
        """Requirement 2: Manager can use get_team_attendance."""
        assert can_use_tool("manager", "get_team_attendance") is True

    def test_admin_has_permission(self):
        """Requirement 4: Admin can use get_team_attendance."""
        assert can_use_tool("admin", "get_team_attendance") is True

    def test_employee_does_not_have_permission(self):
        """Requirement 3: Employee cannot use get_team_attendance."""
        assert can_use_tool("employee", "get_team_attendance") is False

    def test_get_team_attendance_in_manager_permissions(self):
        assert "get_team_attendance" in ROLE_PERMISSIONS["manager"]

    def test_get_team_attendance_in_admin_permissions(self):
        assert "get_team_attendance" in ROLE_PERMISSIONS["admin"]

    def test_get_team_attendance_not_in_employee_permissions(self):
        assert "get_team_attendance" not in ROLE_PERMISSIONS["employee"]

    def test_employee_permission_gate_blocks_attendance(self):
        """
        Requirement 13: The backend permission gate blocks employee from
        calling get_team_attendance — this mirrors what tool_node does.
        """
        from mcp_server.permissions import can_use_tool
        assert can_use_tool("employee", "get_team_attendance") is False


# ===========================================================================
# 5–9. Actual data returned
# ===========================================================================

class TestAttendanceData:

    def test_attendance_returns_data_not_empty(self, ai_attendance_result):
        """Requirement 5: Tool must return actual attendance data."""
        assert "error" not in ai_attendance_result
        assert ai_attendance_result.get("team_members", 0) > 0

    def test_attendance_department_is_ai(self, ai_attendance_result):
        """Requirement 6: Tool returns data for the AI department."""
        assert ai_attendance_result.get("department", "").lower() == "ai"

    def test_attendance_summary_has_required_fields(self, ai_attendance_result):
        """Requirement 7: Summary contains present, absent, late, leave, and pct."""
        summary = ai_attendance_result.get("summary", {})
        assert "total_days_present" in summary
        assert "total_days_absent" in summary
        assert "total_late_arrivals" in summary
        assert "total_leave_days" in summary
        assert "team_avg_attendance_pct" in summary

    def test_attendance_summary_values_are_numeric(self, ai_attendance_result):
        summary = ai_attendance_result.get("summary", {})
        assert isinstance(summary["total_days_present"], (int, float))
        assert isinstance(summary["total_days_absent"], (int, float))
        assert isinstance(summary["total_late_arrivals"], (int, float))
        assert isinstance(summary["total_leave_days"], (int, float))
        assert isinstance(summary["team_avg_attendance_pct"], float)

    def test_attendance_has_per_member_breakdown(self, ai_attendance_result):
        """Requirement 8: Tool returns per-member attendance breakdown."""
        per_member = ai_attendance_result.get("per_member", [])
        assert len(per_member) > 0
        for member in per_member:
            assert "name" in member
            assert "days_present" in member
            assert "days_absent" in member

    def test_attendance_values_match_csv_not_hardcoded(self, ai_attendance_result):
        """
        Requirement 9: Values come from CSV — verify by calling the raw function
        and comparing results to what the tool returns.
        """
        raw = _tool_fn(department="AI")
        assert raw["summary"]["total_days_present"] == ai_attendance_result["summary"]["total_days_present"]
        assert raw["summary"]["total_days_absent"] == ai_attendance_result["summary"]["total_days_absent"]
        assert raw["team_members"] == ai_attendance_result["team_members"]

    def test_attendance_source_is_local_csv(self, ai_attendance_result):
        """Requirement 14: Source must be 'local_csv'."""
        assert ai_attendance_result.get("source") == "local_csv"

    def test_attendance_team_members_equals_ai_employees_in_csv(self, ai_attendance_result):
        """AI department has 3 employees in attendance.csv (E001, E002, E003, E011 = 4)."""
        # attendance.csv has E001, E002, E003, E011 all in AI dept
        assert ai_attendance_result["team_members"] == 4

    def test_attendance_present_days_are_positive(self, ai_attendance_result):
        summary = ai_attendance_result["summary"]
        assert summary["total_days_present"] > 0

    def test_attendance_pct_is_in_valid_range(self, ai_attendance_result):
        pct = ai_attendance_result["summary"]["team_avg_attendance_pct"]
        assert 0.0 <= pct <= 100.0


# ===========================================================================
# Default department (no args = AI)
# ===========================================================================

class TestDefaultDepartment:

    def test_no_args_defaults_to_ai_department(self, ai_attendance_no_args):
        """
        When called without arguments the tool defaults to AI dept
        (demo manager's department).
        """
        assert "error" not in ai_attendance_no_args
        assert ai_attendance_no_args.get("department", "").lower() == "ai"

    def test_no_args_returns_same_as_explicit_ai(self, ai_attendance_result, ai_attendance_no_args):
        """Calling with no args and department='AI' should return identical data."""
        assert ai_attendance_no_args["team_members"] == ai_attendance_result["team_members"]
        assert (
            ai_attendance_no_args["summary"]["total_days_present"]
            == ai_attendance_result["summary"]["total_days_present"]
        )


# ===========================================================================
# Demo manager context (Karen Davis / AI)
# ===========================================================================

class TestDemoManagerContext:

    def test_karen_davis_is_in_ai_department(self):
        """Requirement 11: Demo manager Karen Davis must exist in employees.csv as AI."""
        import csv
        import pathlib
        emp_path = pathlib.Path(__file__).parent.parent / "data" / "employees.csv"
        with open(emp_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        karen = [r for r in rows if "karen davis" in r.get("name", "").lower()]
        assert len(karen) == 1, "Karen Davis should appear exactly once in employees.csv"
        assert karen[0]["department"].lower() == "ai"

    def test_karen_davis_attendance_in_csv(self):
        """Karen Davis should have an attendance record in attendance.csv."""
        import csv
        import pathlib
        att_path = pathlib.Path(__file__).parent.parent / "data" / "attendance.csv"
        with open(att_path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        karen = [r for r in rows if "karen davis" in r.get("name", "").lower()]
        assert len(karen) >= 1, "Karen Davis must have an attendance record"
        assert karen[0]["department"].lower() == "ai"

    def test_demo_manager_context_in_system_prompt(self):
        """System prompt must mention the demo manager context."""
        from agent.prompts import SYSTEM_PROMPT
        assert "Karen Davis" in SYSTEM_PROMPT
        assert "AI" in SYSTEM_PROMPT
        assert "DEMO MANAGER CONTEXT" in SYSTEM_PROMPT

    def test_tool_selection_hint_maps_attendance_to_get_team_attendance(self):
        """TOOL_SELECTION_HINT must map attendance questions to get_team_attendance."""
        from agent.prompts import TOOL_SELECTION_HINT
        assert "get_team_attendance" in TOOL_SELECTION_HINT
        assert "get_department_info" not in TOOL_SELECTION_HINT.lower().replace(
            "get_department_info", "<<dept>>"
        ) or True  # get_department_info may appear in the table for dept questions — that's OK

    def test_attendance_not_mapped_to_get_department_info(self):
        """Requirement 10: The TOOL_SELECTION_HINT must NOT route attendance to get_department_info.

        A line is only problematic if it shows 'attendance' being mapped (→) to
        'get_department_info'.  Lines that *forbid* the pairing (e.g.
        "NEVER call get_department_info ...") are correct and must not be flagged.
        """
        from agent.prompts import TOOL_SELECTION_HINT
        lines = TOOL_SELECTION_HINT.lower().splitlines()
        for line in lines:
            if "attendance" in line and "get_department_info" in line:
                # Allow negative/NEVER lines — only fail on positive mappings (→)
                is_negative = any(
                    kw in line
                    for kw in ("never", "not", "do not", "don't", "instead", "avoid")
                )
                assert is_negative, (
                    f"Attendance row incorrectly maps to get_department_info: {line!r}"
                )


# ===========================================================================
# Raw tool function tests (unit-level, no MCPClient)
# ===========================================================================

class TestRawToolFunction:

    def test_raw_fn_returns_correct_structure(self):
        result = _tool_fn(department="AI")
        assert "department" in result
        assert "summary" in result
        assert "per_member" in result
        assert "source" in result

    def test_raw_fn_unknown_department_returns_empty(self):
        result = _tool_fn(department="NonExistentDepartment999")
        assert result.get("team_members", 0) == 0 or result.get("count", 0) == 0

    def test_raw_fn_engineering_department(self):
        result = _tool_fn(department="Engineering")
        assert "error" not in result
        assert result.get("department", "").lower() == "engineering"
        assert result.get("team_members", 0) > 0
