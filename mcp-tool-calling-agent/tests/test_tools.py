"""
tests/test_tools.py
-------------------
Unit tests for the MCP tool data-access functions.
These tests run directly against the CSV files — no server needed.

Run: pytest tests/test_tools.py -v
"""

import os
import sys
import pytest

# Make sure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Point to real data directory
os.environ["DATA_DIR"] = "data"
os.environ["DOCUMENTS_DIR"] = "documents"

from mcp_server.tools import (
    get_employee_info,
    get_department_info,
    get_project_info,
    search_company_policy,
)


# ===========================================================================
# get_employee_info
# ===========================================================================

class TestGetEmployeeInfo:

    def test_get_employees_by_department(self):
        result = get_employee_info(department="AI")
        assert "employees" in result
        assert result["count"] > 0
        for emp in result["employees"]:
            assert emp["department"] == "AI"

    def test_get_employee_by_id(self):
        result = get_employee_info(employee_id="E001")
        assert result["count"] == 1
        assert result["employees"][0]["employee_id"] == "E001"

    def test_get_all_employees(self):
        result = get_employee_info()
        assert result["count"] >= 10

    def test_department_case_insensitive(self):
        result_upper = get_employee_info(department="AI")
        result_lower = get_employee_info(department="ai")
        assert result_upper["count"] == result_lower["count"]

    def test_nonexistent_department_returns_empty(self):
        result = get_employee_info(department="Nonexistent")
        assert result["count"] == 0
        assert result["employees"] == []

    def test_nonexistent_employee_id_returns_empty(self):
        result = get_employee_info(employee_id="E999")
        assert result["count"] == 0

    def test_invalid_department_empty_string_returns_all(self):
        # Empty string → treated as None → returns all employees
        result = get_employee_info(department="")
        # Empty string is falsy so tool returns all
        assert result["count"] >= 10

    def test_field_filtering(self):
        result = get_employee_info(
            department="AI",
            visible_fields=["employee_id", "name", "department"]
        )
        for emp in result["employees"]:
            assert "access_level" not in emp
            assert "employee_id" in emp
            assert "name" in emp


# ===========================================================================
# get_department_info
# ===========================================================================

class TestGetDepartmentInfo:

    def test_get_all_departments(self):
        result = get_department_info()
        assert "departments" in result
        assert result["count"] >= 4  # AI, Security, HR, Engineering

    def test_get_specific_department(self):
        result = get_department_info(department_name="AI")
        assert result["count"] == 1
        assert result["departments"][0]["department_name"] == "AI"

    def test_department_has_required_fields(self):
        result = get_department_info(department_name="Engineering")
        dept = result["departments"][0]
        assert "department_id" in dept
        assert "department_name" in dept
        assert "manager" in dept
        assert "description" in dept

    def test_nonexistent_department(self):
        result = get_department_info(department_name="Nonexistent")
        assert result["count"] == 0


# ===========================================================================
# get_project_info
# ===========================================================================

class TestGetProjectInfo:

    def test_get_all_projects(self):
        result = get_project_info()
        assert "projects" in result
        assert result["count"] >= 5

    def test_get_project_by_id(self):
        result = get_project_info(project_id="P001")
        assert result["count"] == 1
        assert result["projects"][0]["project_id"] == "P001"

    def test_get_projects_by_department(self):
        result = get_project_info(department="AI")
        assert result["count"] > 0
        for proj in result["projects"]:
            assert proj["department"] == "AI"

    def test_get_active_projects(self):
        result = get_project_info(status="Active")
        assert result["count"] > 0
        for proj in result["projects"]:
            assert proj["status"] == "Active"

    def test_project_has_required_fields(self):
        result = get_project_info(project_id="P001")
        proj = result["projects"][0]
        for field in ["project_id", "project_name", "department", "status", "description", "team_size"]:
            assert field in proj

    def test_nonexistent_project(self):
        result = get_project_info(project_id="P999")
        assert result["count"] == 0


# ===========================================================================
# search_company_policy
# ===========================================================================

class TestSearchCompanyPolicy:

    def test_search_leave_policy(self):
        result = search_company_policy(query="annual leave")
        assert "results" in result
        assert result["count"] > 0

    def test_search_specific_document(self):
        result = search_company_policy(query="password", document="security_policy")
        assert result["count"] > 0
        for r in result["results"]:
            assert r["document"] == "security_policy"

    def test_invalid_document_name(self):
        result = search_company_policy(query="test", document="fake_document")
        assert "error" in result

    def test_empty_query_returns_error(self):
        result = search_company_policy(query="")
        assert "error" in result

    def test_search_returns_excerpts(self):
        result = search_company_policy(query="maternity")
        if result["count"] > 0:
            for r in result["results"]:
                assert "excerpt" in r
                assert "document" in r

    def test_search_all_documents_when_no_document_specified(self):
        result = search_company_policy(query="employee")
        # Should search across all documents
        assert "results" in result

    # ------------------------------------------------------------------
    # Password policy retrieval — the key bug scenario
    # ------------------------------------------------------------------

    def test_search_password_requirements_exact(self):
        """Query "password requirements" must return the security policy chunk."""
        result = search_company_policy(query="password requirements")
        assert result["count"] > 0, "Expected results for 'password requirements'"
        texts = [r["excerpt"].lower() for r in result["results"]]
        assert any("password" in t for t in texts), (
            "Top results should contain password-related content"
        )

    def test_search_password_policy_phrase(self):
        """Query "password policy" must return the password section."""
        result = search_company_policy(query="password policy")
        assert result["count"] > 0
        # At least one result should be from security_policy
        docs = [r["document"] for r in result["results"]]
        assert "security_policy" in docs

    def test_search_natural_language_password_question(self):
        """Natural-language question form must also return useful content."""
        result = search_company_policy(query="what are the password requirements?")
        assert result["count"] > 0, (
            "Natural-language password question should return results"
        )
        texts = [r["excerpt"].lower() for r in result["results"]]
        assert any("password" in t for t in texts)

    def test_search_password_returns_policy_content(self):
        """The returned excerpt must contain actual policy text, not just metadata."""
        result = search_company_policy(
            query="password requirements", document="security_policy"
        )
        assert result["count"] > 0
        top = result["results"][0]
        excerpt = top["excerpt"].lower()
        # The security policy PASSWORD POLICY section mentions these specifics
        assert any(kw in excerpt for kw in ["password", "characters", "mfa", "length", "90"]), (
            f"Excerpt does not contain expected password policy content: {excerpt[:200]}"
        )

    def test_search_password_source_is_local_document(self):
        """The 'source' field must be 'local_document' — used by Streamlit Details panel."""
        result = search_company_policy(query="password requirements")
        assert "source" in result, "'source' key missing from search_company_policy result"
        assert result["source"] != "unknown", (
            f"source should be 'local_document', got: {result['source']}"
        )
        assert result["source"] == "local_document"

    def test_search_password_mode_is_local(self):
        """In DEMO_MODE=true the mode must reflect local search."""
        result = search_company_policy(query="password")
        assert result.get("mode") == "local_keyword_search"
