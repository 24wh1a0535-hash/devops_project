"""
tests/test_permissions.py
--------------------------
Unit tests for the permission/role system.

Run: pytest tests/test_permissions.py -v
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_server.permissions import (
    is_valid_role,
    can_use_tool,
    get_visible_fields,
    permission_check_result,
)


class TestIsValidRole:

    def test_employee_is_valid(self):
        assert is_valid_role("employee") is True

    def test_manager_is_valid(self):
        assert is_valid_role("manager") is True

    def test_admin_is_valid(self):
        assert is_valid_role("admin") is True

    def test_unknown_role_is_invalid(self):
        assert is_valid_role("hacker") is False

    def test_empty_string_is_invalid(self):
        assert is_valid_role("") is False

    def test_role_is_case_insensitive(self):
        assert is_valid_role("ADMIN") is True
        assert is_valid_role("Employee") is True


class TestCanUseTool:

    def test_employee_can_get_department_info(self):
        assert can_use_tool("employee", "get_department_info") is True

    def test_employee_can_get_project_info(self):
        assert can_use_tool("employee", "get_project_info") is True

    def test_employee_can_search_policy(self):
        assert can_use_tool("employee", "search_company_policy") is True

    def test_manager_can_get_employee_info(self):
        assert can_use_tool("manager", "get_employee_info") is True

    def test_admin_can_use_all_tools(self):
        tools = [
            "get_employee_info",
            "get_department_info",
            "get_project_info",
            "search_company_policy",
            "check_user_permission",
        ]
        for tool in tools:
            assert can_use_tool("admin", tool) is True, f"Admin should be able to use {tool}"

    def test_invalid_role_cannot_use_any_tool(self):
        assert can_use_tool("hacker", "get_employee_info") is False

    def test_unknown_tool_returns_false(self):
        assert can_use_tool("admin", "drop_all_tables") is False


class TestGetVisibleFields:

    def test_employee_cannot_see_access_level(self):
        fields = get_visible_fields("employee")
        assert "access_level" not in fields

    def test_manager_can_see_access_level(self):
        fields = get_visible_fields("manager")
        assert "access_level" in fields

    def test_admin_can_see_access_level(self):
        fields = get_visible_fields("admin")
        assert "access_level" in fields

    def test_all_roles_can_see_basic_fields(self):
        for role in ["employee", "manager", "admin"]:
            fields = get_visible_fields(role)
            assert "name" in fields
            assert "department" in fields
            assert "role" in fields


class TestPermissionCheckResult:

    def test_allowed_returns_true(self):
        result = permission_check_result("employee", "get_department_info")
        assert result["allowed"] is True

    def test_denied_returns_false(self):
        # No role should be able to use a fake tool
        result = permission_check_result("employee", "fake_tool")
        assert result["allowed"] is False

    def test_result_contains_required_fields(self):
        result = permission_check_result("manager", "get_employee_info")
        assert "allowed" in result
        assert "role" in result
        assert "tool" in result
        assert "reason" in result

    def test_invalid_role_returns_not_allowed(self):
        result = permission_check_result("unknown_role", "get_employee_info")
        assert result["allowed"] is False
        assert "Unknown role" in result["reason"]
