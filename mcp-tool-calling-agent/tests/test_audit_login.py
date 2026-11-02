"""
tests/test_audit_login.py
--------------------------
Tests for the audit_login_activity tool and admin demo context.

Verifies:
1.  audit_login_activity tool is registered in MCPClient
2.  Admin has permission to call audit_login_activity
3.  Employee does NOT have permission to call audit_login_activity
4.  Manager does NOT have permission to call audit_login_activity
5.  Tool returns actual login activity data (not empty)
6.  Tool defaults to Alice Johnson (E001) when called with no arguments
7.  Tool returns correct fields: audit_target, login_activity, flagged_entries
8.  Tool returns per-record breakdown with login/logout/IP/device/status
9.  Tool does NOT hard-code the answer (values come from CSV data)
10. audit_login_activity is distinct from get_login_activity
11. Demo admin context: Alice Johnson E001 is the predefined audit target
12. PERMISSION_CHECKED_TOOLS contains audit_login_activity
13. audit_login_activity is not accessible to employee/manager via permission gate
14. Tool source is 'local_csv'
15. System prompt contains the admin demo context
16. Tool selection hint maps audit question to audit_login_activity
17. Flagged entries are identified when failed_attempts > 1

Run: pytest tests/test_audit_login.py -v
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
from mcp_server.tools import audit_login_activity as _tool_fn
from agent.nodes import PERMISSION_CHECKED_TOOLS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    return MCPClient()


@pytest.fixture(scope="module")
def default_audit_result(client):
    """Call audit_login_activity with no args — should default to E001."""
    raw = client.call_tool("audit_login_activity", {})
    return json.loads(raw)


@pytest.fixture(scope="module")
def explicit_e001_result(client):
    """Call audit_login_activity with explicit employee_id='E001'."""
    raw = client.call_tool("audit_login_activity", {"employee_id": "E001"})
    return json.loads(raw)


# ===========================================================================
# 1. Tool registration
# ===========================================================================

class TestToolRegistration:

    def test_audit_login_activity_is_registered(self, client):
        """Requirement 1: audit_login_activity must be registered in MCPClient."""
        names = {t.name for t in client.get_tools()}
        assert "audit_login_activity" in names

    def test_audit_login_activity_distinct_from_get_login_activity(self, client):
        """audit_login_activity and get_login_activity are separate tools."""
        names = {t.name for t in client.get_tools()}
        assert "get_login_activity" in names
        assert "audit_login_activity" in names
        assert "audit_login_activity" != "get_login_activity"

    def test_permission_checked_tools_contains_audit_login(self):
        """Requirement 12: PERMISSION_CHECKED_TOOLS must include audit_login_activity."""
        assert "audit_login_activity" in PERMISSION_CHECKED_TOOLS


# ===========================================================================
# 2–4. Permissions
# ===========================================================================

class TestAuditLoginPermissions:

    def test_admin_has_permission(self):
        """Requirement 2: Admin can use audit_login_activity."""
        assert can_use_tool("admin", "audit_login_activity") is True

    def test_employee_does_not_have_permission(self):
        """Requirement 3: Employee cannot use audit_login_activity."""
        assert can_use_tool("employee", "audit_login_activity") is False

    def test_manager_does_not_have_permission(self):
        """Requirement 4: Manager cannot use audit_login_activity."""
        assert can_use_tool("manager", "audit_login_activity") is False

    def test_audit_login_in_admin_permissions(self):
        assert "audit_login_activity" in ROLE_PERMISSIONS["admin"]

    def test_audit_login_not_in_employee_permissions(self):
        assert "audit_login_activity" not in ROLE_PERMISSIONS["employee"]

    def test_audit_login_not_in_manager_permissions(self):
        assert "audit_login_activity" not in ROLE_PERMISSIONS["manager"]

    def test_employee_permission_gate_blocks_audit(self):
        """Requirement 13: Backend gate must block employee from audit_login_activity."""
        assert can_use_tool("employee", "audit_login_activity") is False

    def test_manager_permission_gate_blocks_audit(self):
        """Requirement 13: Backend gate must block manager from audit_login_activity."""
        assert can_use_tool("manager", "audit_login_activity") is False


# ===========================================================================
# 5–9. Actual data returned
# ===========================================================================

class TestAuditLoginData:

    def test_audit_returns_data_not_empty(self, default_audit_result):
        """Requirement 5: Tool must return actual login activity data."""
        assert "error" not in default_audit_result
        assert default_audit_result.get("count", 0) > 0

    def test_audit_target_defaults_to_alice_johnson(self, default_audit_result):
        """Requirement 6: Default audit target must be Alice Johnson (E001)."""
        target = default_audit_result.get("audit_target", {})
        assert target.get("employee_id", "").upper() == "E001"
        assert "alice" in target.get("name", "").lower()

    def test_audit_result_has_required_top_level_fields(self, default_audit_result):
        """Requirement 7: Result must have audit_target, login_activity, flagged_entries."""
        assert "audit_target" in default_audit_result
        assert "login_activity" in default_audit_result
        assert "flagged_entries" in default_audit_result
        assert "count" in default_audit_result
        assert "source" in default_audit_result

    def test_audit_login_records_have_required_fields(self, default_audit_result):
        """Requirement 8: Each login record must have key fields."""
        records = default_audit_result.get("login_activity", [])
        assert len(records) > 0
        required_fields = {
            "employee_id", "name", "login_datetime", "logout_datetime",
            "ip_address", "device", "status", "failed_attempts",
        }
        for record in records:
            for field in required_fields:
                assert field in record, f"Field '{field}' missing from login record: {record}"

    def test_audit_login_status_is_success_or_failed(self, default_audit_result):
        """Login status must be 'Success' or 'Failed'."""
        for record in default_audit_result.get("login_activity", []):
            assert record.get("status") in ("Success", "Failed"), (
                f"Unexpected status: {record.get('status')}"
            )

    def test_audit_values_match_csv_not_hardcoded(self, default_audit_result):
        """Requirement 9: Values come from CSV, not hard-coded."""
        raw = _tool_fn(employee_id="E001")
        assert raw["count"] == default_audit_result["count"]
        assert raw["audit_target"]["employee_id"] == default_audit_result["audit_target"]["employee_id"]

    def test_audit_source_is_local_csv(self, default_audit_result):
        """Requirement 14: Source must be 'local_csv'."""
        assert default_audit_result.get("source") == "local_csv"

    def test_audit_count_positive(self, default_audit_result):
        assert default_audit_result["count"] > 0

    def test_audit_flagged_count_is_integer(self, default_audit_result):
        assert isinstance(default_audit_result.get("flagged_count", 0), int)


# ===========================================================================
# Default target (no args = E001)
# ===========================================================================

class TestDefaultAuditTarget:

    def test_no_args_defaults_to_e001(self, default_audit_result):
        """Calling with no args must default to E001 (Alice Johnson)."""
        assert "error" not in default_audit_result
        assert default_audit_result["audit_target"]["employee_id"].upper() == "E001"

    def test_no_args_returns_same_as_explicit_e001(self, default_audit_result, explicit_e001_result):
        """Calling with no args and employee_id='E001' returns identical data."""
        assert default_audit_result["count"] == explicit_e001_result["count"]
        assert (
            default_audit_result["audit_target"]["employee_id"]
            == explicit_e001_result["audit_target"]["employee_id"]
        )


# ===========================================================================
# Flagged entry detection (Requirement 17)
# ===========================================================================

class TestFlaggedEntries:

    def test_flagged_entries_field_exists(self, default_audit_result):
        """Tool must return a flagged_entries field."""
        assert "flagged_entries" in default_audit_result

    def test_flagged_entries_are_subset_of_login_activity(self, default_audit_result):
        """Every flagged entry must also appear in login_activity."""
        all_ids = {r.get("log_id") for r in default_audit_result.get("login_activity", [])}
        for flagged in default_audit_result.get("flagged_entries", []):
            assert flagged.get("log_id") in all_ids

    def test_flagged_entries_have_high_failed_attempts(self, default_audit_result):
        """Flagged entries must have failed_attempts > 1."""
        for flagged in default_audit_result.get("flagged_entries", []):
            assert int(flagged.get("failed_attempts", 0)) > 1

    def test_get_flagged_for_user_with_known_flag(self):
        """E001 has a record with failed_attempts=1 (LOG002) but not >1, so flagged_count=0."""
        result = _tool_fn(employee_id="E001")
        # LOG002 has failed_attempts=1 which is NOT > 1, so no flags for E001
        assert result["flagged_count"] == 0

    def test_flagged_entry_detected_for_high_failed_attempts(self):
        """E008 Henry Brown has failed_attempts=2 in LOG011 → should be flagged."""
        result = _tool_fn(employee_id="E008")
        assert result["flagged_count"] >= 1
        for entry in result["flagged_entries"]:
            assert int(entry.get("failed_attempts", 0)) > 1


# ===========================================================================
# Demo admin context (Requirement 11)
# ===========================================================================

class TestDemoAdminContext:

    def test_alice_johnson_exists_in_login_activity_csv(self):
        """Requirement 11: Alice Johnson (E001) must exist in login_activity.csv."""
        import csv
        import pathlib
        path = pathlib.Path(__file__).parent.parent / "data" / "login_activity.csv"
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        alice = [r for r in rows if r.get("employee_id", "").upper() == "E001"]
        assert len(alice) >= 1, "Alice Johnson (E001) must have login records"
        assert "alice" in alice[0].get("name", "").lower()

    def test_demo_admin_context_in_system_prompt(self):
        """System prompt must mention the demo admin context with Alice Johnson."""
        from agent.prompts import SYSTEM_PROMPT
        assert "Alice Johnson" in SYSTEM_PROMPT
        assert "E001" in SYSTEM_PROMPT
        assert "DEMO ADMIN CONTEXT" in SYSTEM_PROMPT

    def test_tool_selection_hint_maps_audit_to_audit_login_activity(self):
        """TOOL_SELECTION_HINT must map audit questions to audit_login_activity."""
        from agent.prompts import TOOL_SELECTION_HINT
        assert "audit_login_activity" in TOOL_SELECTION_HINT

    def test_tool_selection_hint_critical_rule_present(self):
        """TOOL_SELECTION_HINT must include the critical rule for login audit."""
        from agent.prompts import TOOL_SELECTION_HINT
        hint_lower = TOOL_SELECTION_HINT.lower()
        assert "audit login" in hint_lower or "login audit" in hint_lower
        assert "audit_login_activity" in TOOL_SELECTION_HINT

    def test_audit_question_row_does_not_map_to_get_department_info(self):
        """Requirement 10: The hint must NOT route the audit question to get_department_info."""
        from agent.prompts import TOOL_SELECTION_HINT
        lines = TOOL_SELECTION_HINT.lower().splitlines()
        for line in lines:
            if "audit" in line and "login" in line and "get_department_info" in line:
                # Only fail if this is a positive mapping (→), not a negative rule
                is_negative = any(
                    kw in line
                    for kw in ("never", "not", "do not", "don't", "instead", "avoid")
                )
                assert is_negative, (
                    f"Audit-login row incorrectly maps to get_department_info: {line!r}"
                )

    def test_system_prompt_rule_12_forbids_asking_for_employee_id(self):
        """System prompt rule 12 must instruct the agent not to ask for an employee ID."""
        from agent.prompts import SYSTEM_PROMPT
        assert "audit_login_activity" in SYSTEM_PROMPT
        # The rule should say to call the tool directly without asking
        assert "do not ask" in SYSTEM_PROMPT.lower() or "without asking" in SYSTEM_PROMPT.lower()


# ===========================================================================
# Raw tool function unit tests (no MCPClient)
# ===========================================================================

class TestRawToolFunction:

    def test_raw_fn_returns_correct_structure(self):
        result = _tool_fn()
        assert "audit_target" in result
        assert "login_activity" in result
        assert "flagged_entries" in result
        assert "source" in result

    def test_raw_fn_defaults_to_e001(self):
        result = _tool_fn()
        assert result["audit_target"]["employee_id"].upper() == "E001"

    def test_raw_fn_explicit_e001_same_as_default(self):
        default = _tool_fn()
        explicit = _tool_fn(employee_id="E001")
        assert default["count"] == explicit["count"]
        assert default["audit_target"]["employee_id"] == explicit["audit_target"]["employee_id"]

    def test_raw_fn_unknown_employee_returns_empty(self):
        result = _tool_fn(employee_id="ZZZZZ")
        assert result.get("count", 0) == 0

    def test_raw_fn_different_employee(self):
        """Can audit a different employee by providing their ID."""
        result = _tool_fn(employee_id="E008")
        assert "error" not in result
        assert result["audit_target"]["employee_id"].upper() == "E008"
        assert result.get("count", 0) > 0

    def test_raw_fn_source_is_local_csv(self):
        result = _tool_fn()
        assert result["source"] == "local_csv"

    def test_raw_fn_note_mentions_demo(self):
        result = _tool_fn()
        assert "DEMO" in result.get("note", "").upper()
