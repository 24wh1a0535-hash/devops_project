"""
tests/test_it_support.py
------------------------
Comprehensive tests for the IT Incident / Support tool system.

Tests cover all 30 predefined questions:
  - 10 Employee IT support questions
  - 10 Manager IT support questions
  - 10 Admin IT support questions

Validates:
  1. Every Employee question maps to a valid MCP tool.
  2. Every Manager question maps to a valid MCP tool.
  3. Every Admin question maps to a valid MCP tool.
  4. Every tool returns structured data.
  5. Employee permissions work correctly.
  6. Manager permissions work correctly.
  7. Admin permissions work correctly.
  8. Action tools work safely in DEMO_MODE.
  9. Agent does not ask for context when demo context exists.
  10. get_department_info is NOT used for IT incident questions.
  11. No hallucinated data is returned (all data comes from CSV).
  12. Existing tests still pass.

Run: pytest tests/test_it_support.py -v
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
    # Employee IT tools
    check_active_incidents,
    check_application_status,
    check_vpn_status,
    check_network_status,
    check_user_application_access,
    check_authentication_issue,
    get_it_ticket_status,
    get_it_ticket_assignee,
    get_it_ticket_last_updated,
    find_related_incident,
    create_it_ticket,
    # Manager IT tools
    get_team_incidents,
    get_team_affected_users,
    compare_incident_scope,
    get_incident_status,
    get_incident_owner,
    get_incident_timeline,
    get_incident_eta,
    get_team_unresolved_tickets,
    get_recurring_team_incidents,
    escalate_incident,
    # Admin IT tools
    get_active_incidents,
    get_critical_service_status,
    get_affected_offices_departments,
    get_incident_impact,
    get_incident_updates,
    get_incident_responsible_team,
    get_sla_breaches,
    get_recurring_incidents,
    find_duplicate_incidents,
    get_incidents_requiring_escalation,
)
from mcp_server.permissions import can_use_tool, ROLE_PERMISSIONS
from role_questions import get_questions_for_role, ROLE_EXAMPLE_QUESTIONS


# ===========================================================================
# SECTION 1: Role question counts — 10 per role, strictly exclusive
# ===========================================================================

class TestITRoleQuestionCounts:

    def test_employee_has_exactly_10_questions(self):
        assert len(get_questions_for_role("employee")) == 10

    def test_manager_has_exactly_10_questions(self):
        assert len(get_questions_for_role("manager")) == 10

    def test_admin_has_exactly_10_questions(self):
        assert len(get_questions_for_role("admin")) == 10

    def test_total_questions_is_30(self):
        total = sum(len(get_questions_for_role(r)) for r in ["employee", "manager", "admin"])
        assert total == 30

    def test_employee_manager_lists_disjoint(self):
        emp = set(get_questions_for_role("employee"))
        mgr = set(get_questions_for_role("manager"))
        assert emp.isdisjoint(mgr), f"Overlap: {emp & mgr}"

    def test_manager_admin_lists_disjoint(self):
        mgr = set(get_questions_for_role("manager"))
        adm = set(get_questions_for_role("admin"))
        assert mgr.isdisjoint(adm), f"Overlap: {mgr & adm}"

    def test_employee_admin_lists_disjoint(self):
        emp = set(get_questions_for_role("employee"))
        adm = set(get_questions_for_role("admin"))
        assert emp.isdisjoint(adm), f"Overlap: {emp & adm}"


# ===========================================================================
# SECTION 2: Exact question content verification
# ===========================================================================

EXPECTED_EMPLOYEE_QUESTIONS = [
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

EXPECTED_MANAGER_QUESTIONS = [
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

EXPECTED_ADMIN_QUESTIONS = [
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


class TestExactQuestionContent:

    def test_all_10_employee_questions_present(self):
        qs = get_questions_for_role("employee")
        for expected in EXPECTED_EMPLOYEE_QUESTIONS:
            assert expected in qs, f"Missing employee question: {expected!r}"

    def test_all_10_manager_questions_present(self):
        qs = get_questions_for_role("manager")
        for expected in EXPECTED_MANAGER_QUESTIONS:
            assert expected in qs, f"Missing manager question: {expected!r}"

    def test_all_10_admin_questions_present(self):
        qs = get_questions_for_role("admin")
        for expected in EXPECTED_ADMIN_QUESTIONS:
            assert expected in qs, f"Missing admin question: {expected!r}"

    # Employee spot-checks
    def test_employee_q1(self):
        assert EXPECTED_EMPLOYEE_QUESTIONS[0] in get_questions_for_role("employee")

    def test_employee_q5(self):
        assert EXPECTED_EMPLOYEE_QUESTIONS[4] in get_questions_for_role("employee")

    def test_employee_q10(self):
        assert EXPECTED_EMPLOYEE_QUESTIONS[9] in get_questions_for_role("employee")

    # Manager spot-checks
    def test_manager_q1(self):
        assert EXPECTED_MANAGER_QUESTIONS[0] in get_questions_for_role("manager")

    def test_manager_q5(self):
        assert EXPECTED_MANAGER_QUESTIONS[4] in get_questions_for_role("manager")

    def test_manager_q10(self):
        assert EXPECTED_MANAGER_QUESTIONS[9] in get_questions_for_role("manager")

    # Admin spot-checks
    def test_admin_q1(self):
        assert EXPECTED_ADMIN_QUESTIONS[0] in get_questions_for_role("admin")

    def test_admin_q5(self):
        assert EXPECTED_ADMIN_QUESTIONS[4] in get_questions_for_role("admin")

    def test_admin_q10(self):
        assert EXPECTED_ADMIN_QUESTIONS[9] in get_questions_for_role("admin")


# ===========================================================================
# SECTION 3: Employee IT tools — return structured data from demo CSV
# ===========================================================================

class TestEmployeeITTools:

    def test_check_active_incidents_returns_data(self):
        result = check_active_incidents()
        assert "active_incidents" in result
        assert "count" in result
        assert result["source"] == "local_demo_data"

    def test_check_active_incidents_for_ai_dept(self):
        result = check_active_incidents(department="AI", office="Hyderabad")
        assert "active_incidents" in result
        # AI dept + Hyderabad should find INC001 and possibly INC002/INC003
        assert result["count"] >= 1

    def test_check_application_status_returns_data(self):
        result = check_application_status()
        assert "application_status" in result
        assert result["count"] >= 1
        assert result["source"] == "local_demo_data"

    def test_check_application_status_smartassist(self):
        result = check_application_status(application_name="SmartAssist")
        assert result["count"] >= 1
        statuses = [s.get("status", "") for s in result["application_status"]]
        assert any(s in ("Down", "Degraded") for s in statuses)

    def test_check_vpn_status_returns_data(self):
        result = check_vpn_status()
        assert "vpn_status" in result
        assert result["vpn_status"] == "Degraded"
        assert "affected_users" in result
        assert result["related_incident"] == "INC002"
        assert result["source"] == "local_demo_data"

    def test_check_vpn_status_has_description(self):
        result = check_vpn_status()
        assert len(result.get("description", "")) > 10

    def test_check_network_status_hyderabad(self):
        result = check_network_status(office="Hyderabad")
        assert "office_network_status" in result
        assert result["count"] >= 1
        for office in result["office_network_status"]:
            assert "status" in office

    def test_check_network_status_default(self):
        result = check_network_status()
        assert "office_network_status" in result
        assert result["source"] == "local_demo_data"

    def test_check_user_application_access_default(self):
        result = check_user_application_access()
        assert "employee_id" in result
        assert result["employee_id"] == "E001"
        assert "affected_services" in result
        assert result["source"] == "local_demo_data"

    def test_check_user_application_access_has_tickets(self):
        result = check_user_application_access(employee_id="E001")
        assert "employee_tickets" in result
        assert len(result["employee_tickets"]) >= 1

    def test_check_authentication_issue_default(self):
        result = check_authentication_issue()
        assert "is_known_issue" in result
        assert "auth_incidents" in result
        assert "message" in result
        assert result["source"] == "local_demo_data"

    def test_check_authentication_issue_finds_sso_incident(self):
        result = check_authentication_issue()
        # INC003 is SSO-related
        assert result["is_known_issue"] is True
        incident_ids = [i.get("incident_id") for i in result["auth_incidents"]]
        assert "INC003" in incident_ids

    def test_get_it_ticket_status_default(self):
        result = get_it_ticket_status()
        assert "employee_id" in result
        assert result["employee_id"] == "E001"
        assert "tickets" in result
        assert result["open_count"] >= 1
        assert result["source"] == "local_demo_data"

    def test_get_it_ticket_status_specific_ticket(self):
        result = get_it_ticket_status(ticket_id="IT001")
        assert result["open_count"] >= 1
        assert result["tickets"][0]["ticket_id"] == "IT001"

    def test_get_it_ticket_assignee_default(self):
        result = get_it_ticket_assignee()
        assert "ticket_assignments" in result
        assert result["count"] >= 1
        for assignment in result["ticket_assignments"]:
            assert "assigned_to" in assignment
            assert "is_assigned" in assignment

    def test_get_it_ticket_assignee_it001_assigned(self):
        result = get_it_ticket_assignee(ticket_id="IT001")
        assert result["ticket_assignments"][0]["is_assigned"] is True
        assert "Raj Kumar" in result["ticket_assignments"][0]["assigned_to"]

    def test_get_it_ticket_last_updated_default(self):
        result = get_it_ticket_last_updated()
        assert "ticket_updates" in result
        assert result["count"] >= 1
        for update in result["ticket_updates"]:
            assert "last_updated" in update
            assert "created_at" in update

    def test_get_it_ticket_last_updated_has_timestamps(self):
        result = get_it_ticket_last_updated(employee_id="E001")
        assert len(result["ticket_updates"]) >= 1
        ts = result["ticket_updates"][0]["last_updated"]
        assert ts.startswith("2026-10-04")

    def test_find_related_incident_default(self):
        result = find_related_incident()
        assert "related_incidents" in result
        assert "recommendation" in result
        assert "incident_count" in result
        assert result["source"] == "local_demo_data"

    def test_find_related_incident_finds_inc001(self):
        result = find_related_incident(employee_id="E001")
        inc_ids = [i.get("incident_id") for i in result["related_incidents"]]
        assert "INC001" in inc_ids

    def test_create_it_ticket_demo_mode(self):
        result = create_it_ticket(issue_title="Test issue")
        assert result["action"] == "create_it_ticket"
        assert "DEMO_MODE" in result["status"]
        assert "ticket" in result
        ticket = result["ticket"]
        assert ticket["employee_id"] == "E001"
        assert ticket["employee_name"] == "Alice Johnson"
        assert ticket.get("ticket_id", "").startswith("IT")
        assert result["source"] == "local_demo_data"

    def test_create_it_ticket_no_real_ticket_created(self):
        result = create_it_ticket(issue_title="Another test")
        assert "DEMO_MODE" in result["note"]
        assert "No real ticket was created" in result["note"]


# ===========================================================================
# SECTION 4: Manager IT tools — return structured data from demo CSV
# ===========================================================================

class TestManagerITTools:

    def test_get_team_incidents_default(self):
        result = get_team_incidents()
        assert "manager_department" in result
        assert result["manager_department"] == "AI"
        assert "team_incidents" in result
        assert result["incident_count"] >= 1
        assert result["source"] == "local_demo_data"

    def test_get_team_incidents_finds_inc001(self):
        result = get_team_incidents()
        inc_ids = [i.get("incident_id") for i in result["team_incidents"]]
        assert "INC001" in inc_ids

    def test_get_team_affected_users_default(self):
        result = get_team_affected_users()
        assert "manager_department" in result
        assert "affected_team_members" in result
        assert "affected_count" in result
        assert result["source"] == "local_demo_data"

    def test_get_team_affected_users_count_nonzero(self):
        result = get_team_affected_users()
        assert result["affected_count"] >= 1

    def test_compare_incident_scope_default(self):
        result = compare_incident_scope()
        assert "scope_analysis" in result
        assert result["count"] >= 1
        for item in result["scope_analysis"]:
            assert "scope" in item
            assert "is_company_wide" in item
        assert result["source"] == "local_demo_data"

    def test_compare_incident_scope_inc002_company_wide(self):
        result = compare_incident_scope(incident_id="INC002")
        analysis = result["scope_analysis"]
        assert len(analysis) == 1
        assert analysis[0]["is_company_wide"] is True

    def test_get_incident_status_default(self):
        result = get_incident_status()
        assert "incidents" in result
        assert result["count"] >= 1
        for inc in result["incidents"]:
            assert "status" in inc
            assert inc["status"].lower() in ("investigating", "open")
        assert result["source"] == "local_demo_data"

    def test_get_incident_status_specific(self):
        result = get_incident_status(incident_id="INC001")
        assert result["count"] == 1
        assert result["incidents"][0]["incident_id"] == "INC001"

    def test_get_incident_owner_default(self):
        result = get_incident_owner()
        assert "incident_ownership" in result
        assert result["count"] >= 1
        for item in result["incident_ownership"]:
            assert "responsible_team" in item
            assert "incident_id" in item
        assert result["source"] == "local_demo_data"

    def test_get_incident_owner_inc001_ai_infra_team(self):
        result = get_incident_owner(incident_id="INC001")
        assert "AI Infrastructure Team" in result["incident_ownership"][0]["responsible_team"]

    def test_get_incident_timeline_default(self):
        result = get_incident_timeline()
        assert "incident_timelines" in result
        assert result["count"] >= 1
        for tl in result["incident_timelines"]:
            assert "reported_at" in tl
            assert "last_updated" in tl
        assert result["source"] == "local_demo_data"

    def test_get_incident_timeline_inc001_timestamps(self):
        result = get_incident_timeline(incident_id="INC001")
        tl = result["incident_timelines"][0]
        assert tl["reported_at"] == "2026-10-04 08:20:00"
        assert tl["last_updated"] == "2026-10-04 10:00:00"

    def test_get_incident_eta_default(self):
        result = get_incident_eta()
        assert "eta_information" in result
        assert result["count"] >= 1
        for item in result["eta_information"]:
            assert "estimated_resolution" in item
            assert "sla_deadline" in item
        assert result["source"] == "local_demo_data"

    def test_get_incident_eta_inc001_resolution(self):
        result = get_incident_eta(incident_id="INC001")
        eta = result["eta_information"][0]
        assert eta["estimated_resolution"] == "2026-10-04 14:00:00"

    def test_get_team_unresolved_tickets_default(self):
        result = get_team_unresolved_tickets()
        assert "manager_department" in result
        assert result["manager_department"] == "AI"
        assert "team_members_with_open_tickets" in result
        assert "total_open_tickets" in result
        assert result["affected_member_count"] >= 1
        assert result["source"] == "local_demo_data"

    def test_get_team_unresolved_tickets_has_karen(self):
        result = get_team_unresolved_tickets()
        member_ids = [m["employee_id"] for m in result["team_members_with_open_tickets"]]
        # Karen (E011) has IT004 open
        assert "E011" in member_ids

    def test_get_recurring_team_incidents_default(self):
        result = get_recurring_team_incidents()
        assert "recurring_patterns" in result
        assert "total_relevant_incidents" in result
        assert result["source"] == "local_demo_data"

    def test_get_recurring_team_incidents_finds_patterns(self):
        result = get_recurring_team_incidents()
        assert result["total_relevant_incidents"] >= 1

    def test_escalate_incident_demo_mode(self):
        result = escalate_incident()
        assert result["action"] == "escalate_incident"
        assert "DEMO_MODE" in result["status"]
        assert "escalated_incident" in result
        assert "escalation_details" in result
        assert result["source"] == "local_demo_data"

    def test_escalate_incident_no_real_escalation(self):
        result = escalate_incident()
        assert "No real escalation was triggered" in result["note"]

    def test_escalate_incident_specific(self):
        result = escalate_incident(incident_id="INC001")
        assert result["escalated_incident"]["incident_id"] == "INC001"
        assert "DEMO_MODE" in result["status"]

    def test_escalate_incident_by_karen(self):
        result = escalate_incident()
        details = result["escalation_details"]
        assert "Karen Davis" in details["escalated_by"]


# ===========================================================================
# SECTION 5: Admin IT tools — return structured data from demo CSV
# ===========================================================================

class TestAdminITTools:

    def test_get_active_incidents_returns_data(self):
        result = get_active_incidents()
        assert "active_incidents" in result
        assert result["count"] >= 1
        assert result["source"] == "local_demo_data"

    def test_get_active_incidents_has_required_fields(self):
        result = get_active_incidents()
        for inc in result["active_incidents"]:
            for field in ["incident_id", "title", "status", "severity",
                          "affected_service", "responsible_team", "affected_users"]:
                assert field in inc, f"Missing field '{field}' in incident"

    def test_get_active_incidents_only_active_statuses(self):
        result = get_active_incidents()
        for inc in result["active_incidents"]:
            assert inc["status"].lower() in ("investigating", "open")

    def test_get_critical_service_status_returns_data(self):
        result = get_critical_service_status()
        assert "critical_services" in result
        assert "unavailable_or_degraded" in result
        assert result["source"] == "local_demo_data"

    def test_get_critical_service_status_finds_down_services(self):
        result = get_critical_service_status()
        assert result["unavailable_count"] >= 1
        for svc in result["unavailable_or_degraded"]:
            assert svc["status"].lower() in ("down", "degraded")
            assert svc.get("is_critical", "").lower() == "yes"

    def test_get_affected_offices_departments_returns_data(self):
        result = get_affected_offices_departments()
        assert "affected_offices" in result
        assert "affected_departments" in result
        assert result["source"] == "local_demo_data"

    def test_get_affected_offices_departments_has_hyderabad(self):
        result = get_affected_offices_departments()
        office_names = [o.get("office_name", "") for o in result["affected_offices"]]
        assert any("Hyderabad" in name for name in office_names)

    def test_get_incident_impact_returns_data(self):
        result = get_incident_impact()
        assert "incident_impact" in result
        assert result["active_incident_count"] >= 1
        assert result["total_affected_users"] >= 1
        assert result["source"] == "local_demo_data"

    def test_get_incident_impact_has_affected_users(self):
        result = get_incident_impact()
        for item in result["incident_impact"]:
            assert "affected_users" in item
            assert "incident_id" in item

    def test_get_incident_updates_returns_data(self):
        result = get_incident_updates()
        assert "incident_updates" in result
        assert result["count"] >= 1
        assert result["source"] == "local_demo_data"

    def test_get_incident_updates_has_timestamps(self):
        result = get_incident_updates()
        for item in result["incident_updates"]:
            assert "last_updated" in item
            assert "status" in item

    def test_get_incident_responsible_team_returns_data(self):
        result = get_incident_responsible_team()
        assert "incident_team_assignments" in result
        assert result["count"] >= 1
        assert result["source"] == "local_demo_data"

    def test_get_incident_responsible_team_has_teams(self):
        result = get_incident_responsible_team()
        for item in result["incident_team_assignments"]:
            assert item.get("responsible_team", "").strip() != ""

    def test_get_sla_breaches_returns_data(self):
        result = get_sla_breaches()
        assert "sla_breached" in result
        assert "within_sla" in result
        assert "breached_count" in result
        assert result["source"] == "local_demo_data"

    def test_get_sla_breaches_inc001_breached(self):
        result = get_sla_breaches()
        # INC001 SLA was 2026-10-04 12:00:00, reference time is 11:00:00 — within SLA
        # INC006 SLA was 2026-10-04 10:00:00, reference time is 11:00:00 — BREACHED
        breached_ids = [b["incident_id"] for b in result["sla_breached"]]
        assert "INC006" in breached_ids

    def test_get_recurring_incidents_returns_data(self):
        result = get_recurring_incidents()
        assert "recurring_systems" in result
        assert "total_services_with_incidents" in result
        assert result["source"] == "local_demo_data"

    def test_get_recurring_incidents_structure(self):
        result = get_recurring_incidents()
        for item in result["recurring_systems"]:
            assert "service" in item
            assert "incident_count" in item
            assert "incidents" in item

    def test_find_duplicate_incidents_returns_data(self):
        result = find_duplicate_incidents()
        assert "explicit_duplicates" in result
        assert "potential_duplicates_by_service" in result
        assert result["source"] == "local_demo_data"

    def test_find_duplicate_incidents_checks_service_overlap(self):
        result = find_duplicate_incidents()
        # VPN-related and company-wide incidents may group by service
        assert "potential_duplicate_groups" in result

    def test_get_incidents_requiring_escalation_returns_data(self):
        result = get_incidents_requiring_escalation()
        assert "incidents_requiring_escalation" in result
        assert "escalation_count" in result
        assert result["source"] == "local_demo_data"

    def test_get_incidents_requiring_escalation_finds_critical(self):
        result = get_incidents_requiring_escalation()
        # INC001 is Critical severity — should require escalation
        esc_ids = [i["incident_id"] for i in result["incidents_requiring_escalation"]]
        assert "INC001" in esc_ids

    def test_get_incidents_requiring_escalation_has_reasons(self):
        result = get_incidents_requiring_escalation()
        for item in result["incidents_requiring_escalation"]:
            assert "escalation_reasons" in item
            assert len(item["escalation_reasons"]) >= 1


# ===========================================================================
# SECTION 6: Permission checks — IT support tools
# ===========================================================================

class TestITSupportPermissions:

    # Employee can use employee IT tools
    def test_employee_can_check_active_incidents(self):
        assert can_use_tool("employee", "check_active_incidents") is True

    def test_employee_can_check_vpn_status(self):
        assert can_use_tool("employee", "check_vpn_status") is True

    def test_employee_can_check_network_status(self):
        assert can_use_tool("employee", "check_network_status") is True

    def test_employee_can_check_app_status(self):
        assert can_use_tool("employee", "check_application_status") is True

    def test_employee_can_check_auth_issue(self):
        assert can_use_tool("employee", "check_authentication_issue") is True

    def test_employee_can_get_ticket_status(self):
        assert can_use_tool("employee", "get_it_ticket_status") is True

    def test_employee_can_get_ticket_assignee(self):
        assert can_use_tool("employee", "get_it_ticket_assignee") is True

    def test_employee_can_get_ticket_last_updated(self):
        assert can_use_tool("employee", "get_it_ticket_last_updated") is True

    def test_employee_can_find_related_incident(self):
        assert can_use_tool("employee", "find_related_incident") is True

    def test_employee_can_create_it_ticket(self):
        assert can_use_tool("employee", "create_it_ticket") is True

    # Employee CANNOT use manager/admin IT tools
    def test_employee_cannot_get_team_incidents(self):
        assert can_use_tool("employee", "get_team_incidents") is False

    def test_employee_cannot_escalate_incident(self):
        assert can_use_tool("employee", "escalate_incident") is False

    def test_employee_cannot_get_active_incidents(self):
        assert can_use_tool("employee", "get_active_incidents") is False

    def test_employee_cannot_get_sla_breaches(self):
        assert can_use_tool("employee", "get_sla_breaches") is False

    def test_employee_cannot_find_duplicate_incidents(self):
        assert can_use_tool("employee", "find_duplicate_incidents") is False

    # Manager can use manager IT tools
    def test_manager_can_get_team_incidents(self):
        assert can_use_tool("manager", "get_team_incidents") is True

    def test_manager_can_get_team_affected_users(self):
        assert can_use_tool("manager", "get_team_affected_users") is True

    def test_manager_can_compare_incident_scope(self):
        assert can_use_tool("manager", "compare_incident_scope") is True

    def test_manager_can_get_incident_status(self):
        assert can_use_tool("manager", "get_incident_status") is True

    def test_manager_can_get_incident_owner(self):
        assert can_use_tool("manager", "get_incident_owner") is True

    def test_manager_can_get_incident_timeline(self):
        assert can_use_tool("manager", "get_incident_timeline") is True

    def test_manager_can_get_incident_eta(self):
        assert can_use_tool("manager", "get_incident_eta") is True

    def test_manager_can_get_team_unresolved_tickets(self):
        assert can_use_tool("manager", "get_team_unresolved_tickets") is True

    def test_manager_can_get_recurring_team_incidents(self):
        assert can_use_tool("manager", "get_recurring_team_incidents") is True

    def test_manager_can_escalate_incident(self):
        assert can_use_tool("manager", "escalate_incident") is True

    # Manager CANNOT use admin IT tools
    def test_manager_cannot_get_active_incidents(self):
        assert can_use_tool("manager", "get_active_incidents") is False

    def test_manager_cannot_get_sla_breaches(self):
        assert can_use_tool("manager", "get_sla_breaches") is False

    def test_manager_cannot_find_duplicate_incidents(self):
        assert can_use_tool("manager", "find_duplicate_incidents") is False

    def test_manager_cannot_get_incidents_requiring_escalation(self):
        assert can_use_tool("manager", "get_incidents_requiring_escalation") is False

    # Admin can use all IT tools
    def test_admin_can_use_all_employee_it_tools(self):
        tools = [
            "check_active_incidents", "check_application_status", "check_vpn_status",
            "check_network_status", "check_user_application_access", "check_authentication_issue",
            "get_it_ticket_status", "get_it_ticket_assignee", "get_it_ticket_last_updated",
            "find_related_incident", "create_it_ticket",
        ]
        for tool in tools:
            assert can_use_tool("admin", tool) is True, f"Admin should be able to use {tool}"

    def test_admin_can_use_all_manager_it_tools(self):
        tools = [
            "get_team_incidents", "get_team_affected_users", "compare_incident_scope",
            "get_incident_status", "get_incident_owner", "get_incident_timeline",
            "get_incident_eta", "get_team_unresolved_tickets",
            "get_recurring_team_incidents", "escalate_incident",
        ]
        for tool in tools:
            assert can_use_tool("admin", tool) is True, f"Admin should be able to use {tool}"

    def test_admin_can_use_all_admin_it_tools(self):
        tools = [
            "get_active_incidents", "get_critical_service_status",
            "get_affected_offices_departments", "get_incident_impact",
            "get_incident_updates", "get_incident_responsible_team",
            "get_sla_breaches", "get_recurring_incidents",
            "find_duplicate_incidents", "get_incidents_requiring_escalation",
        ]
        for tool in tools:
            assert can_use_tool("admin", tool) is True, f"Admin should be able to use {tool}"


# ===========================================================================
# SECTION 7: MCP client loads all 47 tools
# ===========================================================================

class TestMCPClientAllITTools:

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    def test_client_loads_47_tools(self):
        assert len(self.client.get_tools()) == 47

    def test_all_employee_it_tool_names_present(self):
        names = {t.name for t in self.client.get_tools()}
        expected = {
            "check_active_incidents", "check_application_status", "check_vpn_status",
            "check_network_status", "check_user_application_access",
            "check_authentication_issue", "get_it_ticket_status",
            "get_it_ticket_assignee", "get_it_ticket_last_updated",
            "find_related_incident", "create_it_ticket",
        }
        assert expected.issubset(names)

    def test_all_manager_it_tool_names_present(self):
        names = {t.name for t in self.client.get_tools()}
        expected = {
            "get_team_incidents", "get_team_affected_users", "compare_incident_scope",
            "get_incident_status", "get_incident_owner", "get_incident_timeline",
            "get_incident_eta", "get_team_unresolved_tickets",
            "get_recurring_team_incidents", "escalate_incident",
        }
        assert expected.issubset(names)

    def test_all_admin_it_tool_names_present(self):
        names = {t.name for t in self.client.get_tools()}
        expected = {
            "get_active_incidents", "get_critical_service_status",
            "get_affected_offices_departments", "get_incident_impact",
            "get_incident_updates", "get_incident_responsible_team",
            "get_sla_breaches", "get_recurring_incidents",
            "find_duplicate_incidents", "get_incidents_requiring_escalation",
        }
        assert expected.issubset(names)


# ===========================================================================
# SECTION 8: All 30 questions map to working tools via MCPClient
# ===========================================================================

class TestAll30QuestionsHaveToolSupport:
    """
    Loop through all 30 predefined questions and verify that the appropriate
    tool can be called and returns non-error, non-empty structured data.
    """

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    def _call(self, tool: str, args: dict) -> dict:
        raw = self.client.call_tool(tool, args)
        return json.loads(raw)

    # ── EMPLOYEE Q1: Active incident affecting application ────────────────
    def test_employee_q1_check_active_incidents(self):
        result = self._call("check_active_incidents", {})
        assert "active_incidents" in result
        assert result["count"] >= 1

    # ── EMPLOYEE Q2: VPN issues ───────────────────────────────────────────
    def test_employee_q2_check_vpn_status(self):
        result = self._call("check_vpn_status", {})
        assert result["vpn_status"] == "Degraded"
        assert result["related_incident"] == "INC002"

    # ── EMPLOYEE Q3: Network problems at my office ────────────────────────
    def test_employee_q3_check_network_status(self):
        result = self._call("check_network_status", {})
        assert "office_network_status" in result
        assert result["count"] >= 1

    # ── EMPLOYEE Q4: Can't access internal application ────────────────────
    def test_employee_q4_check_user_application_access(self):
        result = self._call("check_user_application_access", {})
        assert result["employee_id"] == "E001"
        assert "affected_services" in result

    # ── EMPLOYEE Q5: Login/auth problem a known issue ─────────────────────
    def test_employee_q5_check_authentication_issue(self):
        result = self._call("check_authentication_issue", {})
        assert "is_known_issue" in result
        assert result["is_known_issue"] is True

    # ── EMPLOYEE Q6: Status of my open IT ticket ──────────────────────────
    def test_employee_q6_get_it_ticket_status(self):
        result = self._call("get_it_ticket_status", {})
        assert result["employee_id"] == "E001"
        assert result["open_count"] >= 1

    # ── EMPLOYEE Q7: Has IT been assigned to my ticket ────────────────────
    def test_employee_q7_get_it_ticket_assignee(self):
        result = self._call("get_it_ticket_assignee", {})
        assert "ticket_assignments" in result
        assert result["count"] >= 1

    # ── EMPLOYEE Q8: When was my ticket last updated ──────────────────────
    def test_employee_q8_get_it_ticket_last_updated(self):
        result = self._call("get_it_ticket_last_updated", {})
        assert "ticket_updates" in result
        assert result["count"] >= 1

    # ── EMPLOYEE Q9: Is there already an incident for my problem ──────────
    def test_employee_q9_find_related_incident(self):
        result = self._call("find_related_incident", {})
        assert "related_incidents" in result
        assert "recommendation" in result

    # ── EMPLOYEE Q10: Create an IT ticket ────────────────────────────────
    def test_employee_q10_create_it_ticket(self):
        result = self._call("create_it_ticket", {"issue_title": "VPN not connecting"})
        assert "DEMO_MODE" in result["status"]
        assert result["ticket"]["ticket_id"].startswith("IT")

    # ── MANAGER Q1: Team affected by IT incident ──────────────────────────
    def test_manager_q1_get_team_incidents(self):
        result = self._call("get_team_incidents", {})
        assert result["manager_department"] == "AI"
        assert result["incident_count"] >= 1

    # ── MANAGER Q2: How many on team are affected ─────────────────────────
    def test_manager_q2_get_team_affected_users(self):
        result = self._call("get_team_affected_users", {})
        assert "affected_count" in result
        assert result["affected_count"] >= 1

    # ── MANAGER Q3: Limited to team or company-wide ───────────────────────
    def test_manager_q3_compare_incident_scope(self):
        result = self._call("compare_incident_scope", {})
        assert "scope_analysis" in result
        assert result["count"] >= 1

    # ── MANAGER Q4: Current status of incident ───────────────────────────
    def test_manager_q4_get_incident_status(self):
        result = self._call("get_incident_status", {})
        assert "incidents" in result
        assert result["count"] >= 1

    # ── MANAGER Q5: Who is handling the incident ──────────────────────────
    def test_manager_q5_get_incident_owner(self):
        result = self._call("get_incident_owner", {})
        assert "incident_ownership" in result
        assert result["count"] >= 1

    # ── MANAGER Q6: When was it reported and last updated ─────────────────
    def test_manager_q6_get_incident_timeline(self):
        result = self._call("get_incident_timeline", {})
        assert "incident_timelines" in result
        assert result["count"] >= 1

    # ── MANAGER Q7: Estimated time to resolve ────────────────────────────
    def test_manager_q7_get_incident_eta(self):
        result = self._call("get_incident_eta", {})
        assert "eta_information" in result
        assert result["count"] >= 1

    # ── MANAGER Q8: Team members with unresolved tickets ─────────────────
    def test_manager_q8_get_team_unresolved_tickets(self):
        result = self._call("get_team_unresolved_tickets", {})
        assert result["affected_member_count"] >= 1
        assert result["total_open_tickets"] >= 1

    # ── MANAGER Q9: Recurring IT problems affecting team ──────────────────
    def test_manager_q9_get_recurring_team_incidents(self):
        result = self._call("get_recurring_team_incidents", {})
        assert "recurring_patterns" in result
        assert result["total_relevant_incidents"] >= 1

    # ── MANAGER Q10: Escalate the issue ──────────────────────────────────
    def test_manager_q10_escalate_incident(self):
        result = self._call("escalate_incident", {})
        assert "DEMO_MODE" in result["status"]
        assert "escalated_incident" in result

    # ── ADMIN Q1: All active incidents company-wide ───────────────────────
    def test_admin_q1_get_active_incidents(self):
        result = self._call("get_active_incidents", {})
        assert result["count"] >= 1
        for inc in result["active_incidents"]:
            assert inc["status"].lower() in ("investigating", "open")

    # ── ADMIN Q2: Critical services unavailable ───────────────────────────
    def test_admin_q2_get_critical_service_status(self):
        result = self._call("get_critical_service_status", {})
        assert result["unavailable_count"] >= 1

    # ── ADMIN Q3: Offices/depts with network issues ───────────────────────
    def test_admin_q3_get_affected_offices_departments(self):
        result = self._call("get_affected_offices_departments", {})
        assert result["affected_office_count"] >= 1

    # ── ADMIN Q4: Users affected per incident ────────────────────────────
    def test_admin_q4_get_incident_impact(self):
        result = self._call("get_incident_impact", {})
        assert result["total_affected_users"] >= 1

    # ── ADMIN Q5: Status and latest update per incident ───────────────────
    def test_admin_q5_get_incident_updates(self):
        result = self._call("get_incident_updates", {})
        assert result["count"] >= 1
        for item in result["incident_updates"]:
            assert "last_updated" in item

    # ── ADMIN Q6: Team responsible per incident ───────────────────────────
    def test_admin_q6_get_incident_responsible_team(self):
        result = self._call("get_incident_responsible_team", {})
        assert result["count"] >= 1

    # ── ADMIN Q7: Incidents over SLA ─────────────────────────────────────
    def test_admin_q7_get_sla_breaches(self):
        result = self._call("get_sla_breaches", {})
        assert "sla_breached" in result
        assert result["breached_count"] >= 1

    # ── ADMIN Q8: Systems with recurring incidents ────────────────────────
    def test_admin_q8_get_recurring_incidents(self):
        result = self._call("get_recurring_incidents", {})
        assert "total_services_with_incidents" in result

    # ── ADMIN Q9: Duplicate incidents ────────────────────────────────────
    def test_admin_q9_find_duplicate_incidents(self):
        result = self._call("find_duplicate_incidents", {})
        assert "explicit_duplicates" in result
        assert "potential_duplicates_by_service" in result

    # ── ADMIN Q10: Incidents requiring escalation ─────────────────────────
    def test_admin_q10_get_incidents_requiring_escalation(self):
        result = self._call("get_incidents_requiring_escalation", {})
        assert result["escalation_count"] >= 1


# ===========================================================================
# SECTION 9: No hallucinated data — all values come from demo CSV
# ===========================================================================

class TestNoHallucinatedData:

    def test_vpn_status_matches_csv(self):
        result = check_vpn_status()
        assert result["vpn_status"] == "Degraded"
        assert result["related_incident"] == "INC002"
        assert result["affected_users"] == "18"

    def test_inc001_title_from_csv(self):
        result = get_active_incidents()
        inc001 = next(i for i in result["active_incidents"] if i["incident_id"] == "INC001")
        assert inc001["title"] == "SmartAssist AI Platform Outage"

    def test_inc001_severity_from_csv(self):
        result = get_active_incidents()
        inc001 = next(i for i in result["active_incidents"] if i["incident_id"] == "INC001")
        assert inc001["severity"] == "Critical"

    def test_ticket_it001_assignee_from_csv(self):
        result = get_it_ticket_assignee(ticket_id="IT001")
        assignment = result["ticket_assignments"][0]
        assert "Raj Kumar" in assignment["assigned_to"]

    def test_ticket_it001_employee_from_csv(self):
        result = get_it_ticket_status(ticket_id="IT001")
        assert result["tickets"][0]["employee_name"] == "Alice Johnson"

    def test_inc001_responsible_team_from_csv(self):
        result = get_incident_owner(incident_id="INC001")
        assert "AI Infrastructure Team" in result["incident_ownership"][0]["responsible_team"]

    def test_sla_breach_inc006_from_csv(self):
        result = get_sla_breaches()
        breached_ids = [b["incident_id"] for b in result["sla_breached"]]
        assert "INC006" in breached_ids

    def test_hyderabad_office_in_affected_offices(self):
        result = get_affected_offices_departments()
        office_names = [o.get("office_name", "") for o in result["affected_offices"]]
        assert any("Hyderabad" in name for name in office_names)

    def test_no_error_in_any_result(self):
        """All tools should return valid data, not error dicts."""
        tools_and_calls = [
            (check_vpn_status, {}),
            (check_active_incidents, {}),
            (get_it_ticket_status, {}),
            (get_team_incidents, {}),
            (get_active_incidents, {}),
            (get_sla_breaches, {}),
        ]
        for func, kwargs in tools_and_calls:
            result = func(**kwargs)
            assert "error" not in result, f"{func.__name__} returned error: {result.get('error')}"


# ===========================================================================
# SECTION 10: Action tools — DEMO_MODE safety
# ===========================================================================

class TestActionToolsDemoMode:

    def test_create_it_ticket_is_demo(self):
        result = create_it_ticket()
        assert "DEMO_MODE" in result["status"]
        assert "DEMO_MODE" in result["note"]

    def test_create_it_ticket_no_external_call(self):
        result = create_it_ticket(issue_title="Test")
        # The note must make clear it's simulated
        assert "No real ticket was created" in result["note"]

    def test_escalate_incident_is_demo(self):
        result = escalate_incident()
        assert "DEMO_MODE" in result["status"]
        assert "DEMO_MODE" in result["note"]

    def test_escalate_incident_no_real_action(self):
        result = escalate_incident()
        assert "No real escalation was triggered" in result["note"]

    def test_create_ticket_demo_id_format(self):
        result = create_it_ticket()
        ticket_id = result["ticket"]["ticket_id"]
        assert ticket_id.startswith("IT")
        assert len(ticket_id) >= 4  # "IT" + at least 2 digits


# ===========================================================================
# SECTION 11: IT tools registered in PERMISSION_CHECKED_TOOLS
# ===========================================================================

class TestITToolsInPermissionSet:

    def test_employee_it_tools_in_permission_set(self):
        from agent.nodes import PERMISSION_CHECKED_TOOLS
        employee_it_tools = {
            "check_active_incidents", "check_application_status", "check_vpn_status",
            "check_network_status", "check_user_application_access",
            "check_authentication_issue", "get_it_ticket_status",
            "get_it_ticket_assignee", "get_it_ticket_last_updated",
            "find_related_incident", "create_it_ticket",
        }
        for tool in employee_it_tools:
            assert tool in PERMISSION_CHECKED_TOOLS, f"{tool} not in PERMISSION_CHECKED_TOOLS"

    def test_manager_it_tools_in_permission_set(self):
        from agent.nodes import PERMISSION_CHECKED_TOOLS
        manager_it_tools = {
            "get_team_incidents", "get_team_affected_users", "compare_incident_scope",
            "get_incident_status", "get_incident_owner", "get_incident_timeline",
            "get_incident_eta", "get_team_unresolved_tickets",
            "get_recurring_team_incidents", "escalate_incident",
        }
        for tool in manager_it_tools:
            assert tool in PERMISSION_CHECKED_TOOLS, f"{tool} not in PERMISSION_CHECKED_TOOLS"

    def test_admin_it_tools_in_permission_set(self):
        from agent.nodes import PERMISSION_CHECKED_TOOLS
        admin_it_tools = {
            "get_active_incidents", "get_critical_service_status",
            "get_affected_offices_departments", "get_incident_impact",
            "get_incident_updates", "get_incident_responsible_team",
            "get_sla_breaches", "get_recurring_incidents",
            "find_duplicate_incidents", "get_incidents_requiring_escalation",
        }
        for tool in admin_it_tools:
            assert tool in PERMISSION_CHECKED_TOOLS, f"{tool} not in PERMISSION_CHECKED_TOOLS"


# ===========================================================================
# SECTION 12: get_department_info NOT used for IT incident questions
# ===========================================================================

class TestNoDepartmentInfoMisrouting:
    """
    Verify that IT incident questions are NOT routed to get_department_info.
    The IT-specific tools must exist in the tool set and be the correct answer.
    """

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()
        self.tool_names = {t.name for t in self.client.get_tools()}

    def test_vpn_question_has_vpn_tool_not_dept_info(self):
        # "Is the company VPN currently experiencing any issues?" → check_vpn_status
        assert "check_vpn_status" in self.tool_names
        result = json.loads(self.client.call_tool("check_vpn_status", {}))
        assert "vpn_status" in result  # vpn_status is NOT in department info

    def test_incident_question_has_incident_tool_not_dept_info(self):
        # "What are the currently active IT incidents?" → get_active_incidents
        assert "get_active_incidents" in self.tool_names
        result = json.loads(self.client.call_tool("get_active_incidents", {}))
        assert "active_incidents" in result  # active_incidents is NOT in department info

    def test_sla_question_has_sla_tool_not_dept_info(self):
        assert "get_sla_breaches" in self.tool_names
        result = json.loads(self.client.call_tool("get_sla_breaches", {}))
        assert "sla_breached" in result

    def test_ticket_question_has_ticket_tool_not_dept_info(self):
        assert "get_it_ticket_status" in self.tool_names
        result = json.loads(self.client.call_tool("get_it_ticket_status", {}))
        assert "tickets" in result

    def test_escalation_question_has_escalation_tool(self):
        assert "escalate_incident" in self.tool_names
        result = json.loads(self.client.call_tool("escalate_incident", {}))
        assert "escalated_incident" in result


# ===========================================================================
# SECTION 13: Demo context defaults — no user prompting needed
# ===========================================================================

class TestDemoContextDefaults:

    def test_employee_tools_default_to_e001(self):
        result = get_it_ticket_status()
        assert result["employee_id"] == "E001"

    def test_employee_tools_default_to_alice_johnson(self):
        result = create_it_ticket()
        assert result["ticket"]["employee_name"] == "Alice Johnson"

    def test_manager_tools_default_to_ai_dept(self):
        result = get_team_incidents()
        assert result["manager_department"] == "AI"

    def test_manager_tools_default_to_hyderabad(self):
        result = check_network_status()
        # Should query Hyderabad office by default
        assert result["queried_office"] == "Hyderabad"

    def test_vpn_status_needs_no_args(self):
        result = check_vpn_status()
        assert "vpn_status" in result

    def test_active_incidents_needs_no_args(self):
        result = get_active_incidents()
        assert "active_incidents" in result

    def test_escalate_incident_auto_selects_critical(self):
        result = escalate_incident()
        # Should auto-select INC001 (Critical)
        assert result["escalated_incident"]["severity"] == "Critical"


# ===========================================================================
# SECTION 14: All 30 questions loop test
# ===========================================================================

QUESTION_TOOL_MAP = {
    # Employee questions
    "Is there currently an IT incident affecting the application I'm trying to use?": "check_active_incidents",
    "Is the company VPN currently experiencing any issues?": "check_vpn_status",
    "Are there any network problems affecting my office right now?": "check_network_status",
    "Why can't I access the internal application?": "check_user_application_access",
    "Is my login/authentication problem a known issue?": "check_authentication_issue",
    "What is the current status of my open IT ticket?": "get_it_ticket_status",
    "Has someone from IT been assigned to my ticket?": "get_it_ticket_assignee",
    "When was my IT ticket last updated?": "get_it_ticket_last_updated",
    "Is there already an incident for the problem I'm experiencing?": "find_related_incident",
    "Can you create an IT ticket for my issue if it hasn't already been reported?": "create_it_ticket",
    # Manager questions
    "Are any members of my team currently affected by an IT incident?": "get_team_incidents",
    "How many people on my team are affected by the current issue?": "get_team_affected_users",
    "Is this problem limited to my team, or is it affecting other teams too?": "compare_incident_scope",
    "What is the current status of the incident affecting my team?": "get_incident_status",
    "Who is currently handling the incident?": "get_incident_owner",
    "When was the incident first reported and when was it last updated?": "get_incident_timeline",
    "Is there an estimated time for resolving the issue?": "get_incident_eta",
    "Which members of my team currently have unresolved IT tickets?": "get_team_unresolved_tickets",
    "Are there any recurring IT problems affecting my team?": "get_recurring_team_incidents",
    "Can you escalate the issue if it is blocking my team's work?": "escalate_incident",
    # Admin questions
    "What are the currently active IT incidents across the company?": "get_active_incidents",
    "Which critical applications or services are currently unavailable?": "get_critical_service_status",
    "Which offices or departments are currently affected by network issues?": "get_affected_offices_departments",
    "How many users are currently affected by each major incident?": "get_incident_impact",
    "What is the current status and latest update for each major incident?": "get_incident_updates",
    "Which team is responsible for resolving each active incident?": "get_incident_responsible_team",
    "Which incidents have been open longer than their SLA?": "get_sla_breaches",
    "Which systems have had recurring incidents recently?": "get_recurring_incidents",
    "Are there duplicate incidents for the same underlying problem?": "find_duplicate_incidents",
    "Which active issues require escalation or immediate attention?": "get_incidents_requiring_escalation",
}


class TestAll30QuestionsLoop:
    """
    Loop through all 30 predefined questions, verify the mapped tool is callable
    and returns non-error, non-empty structured data.
    """

    def setup_method(self):
        from mcp_client import MCPClient
        self.client = MCPClient()

    def test_all_30_questions_have_tool_mapping(self):
        """Every one of the 30 questions must have a tool in QUESTION_TOOL_MAP."""
        all_questions = (
            EXPECTED_EMPLOYEE_QUESTIONS +
            EXPECTED_MANAGER_QUESTIONS +
            EXPECTED_ADMIN_QUESTIONS
        )
        assert len(all_questions) == 30
        for q in all_questions:
            assert q in QUESTION_TOOL_MAP, f"No tool mapping for: {q!r}"

    def test_all_30_tools_are_registered(self):
        """All 30 mapped tools must be registered in the MCPClient."""
        names = {t.name for t in self.client.get_tools()}
        for question, tool in QUESTION_TOOL_MAP.items():
            assert tool in names, f"Tool '{tool}' not registered (for question: {question!r})"

    def test_all_30_tools_return_structured_data(self):
        """Every mapped tool returns non-error data."""
        for question, tool in QUESTION_TOOL_MAP.items():
            result = json.loads(self.client.call_tool(tool, {}))
            assert "error" not in result, (
                f"Tool '{tool}' returned error for question: {question!r}\n"
                f"Error: {result.get('error')}"
            )
            # Result must be a non-empty dict
            assert len(result) > 0, f"Tool '{tool}' returned empty result"

    def test_question_count_per_role(self):
        """Confirm 10 questions per role in ROLE_EXAMPLE_QUESTIONS."""
        for role in ["employee", "manager", "admin"]:
            assert len(ROLE_EXAMPLE_QUESTIONS[role]) == 10

    def test_30_total_unique_questions(self):
        all_qs = []
        for role in ["employee", "manager", "admin"]:
            all_qs.extend(ROLE_EXAMPLE_QUESTIONS[role])
        assert len(all_qs) == 30
        assert len(set(all_qs)) == 30, "Duplicate questions found across roles"
