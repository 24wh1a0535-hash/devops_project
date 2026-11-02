"""
mcp_client.py
-------------
MCP Client: bridges the LangGraph agent and the MCP server.

In DEMO_MODE (DEMO_MODE=true), the client calls the tool functions directly
in the same process (no network needed). This makes local development
and testing simple while preserving the MCP architecture.

All 13 tools are registered:

Existing (5):
    get_employee_info, get_department_info, get_project_info,
    search_company_policy, check_user_permission

New Employee tools (2):
    get_leave_balance, get_hr_info

New Manager tools (2):
    get_team_leave_info, get_team_utilization

New Admin tools (4):
    admin_manage_user, get_compliance_training_status,
    get_login_activity, get_admin_permissions
"""

import json
import logging
import os
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ===========================================================================
# Pydantic input schemas
# ===========================================================================

class GetEmployeeInfoInput(BaseModel):
    department: str = Field(default="", description="Department name to filter (e.g. 'AI', 'Engineering'). Leave empty for all.")
    employee_id: str = Field(default="", description="Specific employee ID (e.g. 'E001'). Leave empty to not filter by ID.")
    user_role: str = Field(default="employee", description="Requesting user role: employee, manager, or admin.")


class GetDepartmentInfoInput(BaseModel):
    department_name: str = Field(default="", description="Name of the department to look up. Leave empty for all departments.")


class GetProjectInfoInput(BaseModel):
    project_id: str = Field(default="", description="Project ID (e.g. 'P001'). Leave empty to not filter.")
    department: str = Field(default="", description="Filter projects by department. Leave empty to not filter.")
    status: str = Field(default="", description="Filter by status: 'Active', 'Completed', or 'In Progress'. Leave empty for all.")


class SearchCompanyPolicyInput(BaseModel):
    query: str = Field(description="Search keywords or question about company policies.")
    document: str = Field(default="", description="Specific document: 'company_policy', 'leave_policy', 'security_policy'. Leave empty for all.")


class CheckUserPermissionInput(BaseModel):
    role: str = Field(description="User role to check: employee, manager, or admin.")
    tool_name: str = Field(description="Tool name to check access for.")


class GetLeaveBalanceInput(BaseModel):
    employee_id: str = Field(default="", description="Employee ID (e.g. 'E001'). Leave empty to not filter by ID.")
    employee_name: str = Field(default="", description="Employee name (partial match). Leave empty if using employee_id.")
    department: str = Field(default="", description="Department name to filter leave balances. Leave empty for all.")


class GetHRInfoInput(BaseModel):
    info_type: str = Field(description="What to retrieve: 'hr_contact', 'timesheet', or 'performance'.")
    department: str = Field(default="", description="Department name (for hr_contact and performance).")
    month: str = Field(default="", description="Month name (e.g. 'October') for timesheet deadlines.")
    year: str = Field(default="", description="Year (e.g. '2026') for timesheet deadlines.")


class GetTeamLeaveInfoInput(BaseModel):
    manager_department: str = Field(default="", description="Manager's department name (e.g. 'AI', 'Engineering').")
    info_type: str = Field(default="pending", description="What to retrieve: 'pending' (leave requests), 'upcoming' (next 2 weeks), 'attendance' (monthly summary).")


class GetTeamAttendanceInput(BaseModel):
    department: str = Field(default="", description="Department / team name (e.g. 'AI'). Leave empty to use the demo manager's department (AI).")
    month: str = Field(default="", description="Month name (e.g. 'September'). Leave empty to use the most recent available month.")
    year: str = Field(default="", description="Year (e.g. '2026'). Leave empty to use the most recent available year.")


class GetTeamUtilizationInput(BaseModel):
    department: str = Field(default="", description="Department name to filter. Leave empty for all departments.")


class AdminManageUserInput(BaseModel):
    action: str = Field(description="Action to perform: 'onboard', 'revoke_access', 'restore_account', 'headcount_report', 'get_accounts'.")
    employee_id: str = Field(default="", description="Employee ID for user-specific actions.")
    employee_name: str = Field(default="", description="Employee name for user-specific actions.")
    department: str = Field(default="", description="Department filter for headcount or account listing.")


class GetComplianceTrainingStatusInput(BaseModel):
    employee_id: str = Field(default="", description="Filter by employee ID.")
    department: str = Field(default="", description="Filter by department.")
    status_filter: str = Field(default="", description="Filter by status: 'Not Started', 'In Progress', 'Completed'. Leave empty for all incomplete.")


class GetLoginActivityInput(BaseModel):
    employee_id: str = Field(default="", description="Filter by employee ID.")
    employee_name: str = Field(default="", description="Filter by employee name (partial match).")
    username: str = Field(default="", description="Filter by system username.")
    limit: int = Field(default=10, description="Maximum number of log entries to return.")


class AuditLoginActivityInput(BaseModel):
    employee_id: str = Field(
        default="",
        description=(
            "Employee ID to audit (e.g. 'E001'). "
            "Leave empty to use the default demo audit target: Alice Johnson (E001)."
        ),
    )
    employee_name: str = Field(
        default="",
        description="Employee name override (partial match). Used only when employee_id is also overridden.",
    )
    limit: int = Field(default=10, description="Maximum number of log entries to return.")


class GetHeadcountReportInput(BaseModel):
    department: str = Field(
        default="",
        description=(
            "Optional department name to filter (e.g. 'AI', 'Engineering'). "
            "Leave empty to get organisation-wide headcount across all departments."
        ),
    )


class GetAdminPermissionsInput(BaseModel):
    employee_id: str = Field(default="", description="Filter by employee ID. Leave empty to list all privileged accounts.")
    permission_level: str = Field(default="", description="Filter by level: 'admin' or 'elevated'. Leave empty for all.")


# ---------------------------------------------------------------------------
# IT Support Pydantic schemas
# ---------------------------------------------------------------------------

class CheckActiveIncidentsInput(BaseModel):
    employee_id: str = Field(default="", description="Employee ID. Leave empty to use demo default (E001 — Alice Johnson).")
    department: str = Field(default="", description="Department. Leave empty to use demo default (AI).")
    office: str = Field(default="", description="Office. Leave empty to use demo default (Hyderabad).")


class CheckApplicationStatusInput(BaseModel):
    application_name: str = Field(default="", description="Application name to check. Leave empty for all affected apps.")
    department: str = Field(default="", description="Department context. Leave empty for demo default (AI).")


class CheckVPNStatusInput(BaseModel):
    pass  # no parameters needed


class CheckNetworkStatusInput(BaseModel):
    office: str = Field(default="", description="Office or city name. Leave empty for demo default (Hyderabad).")
    department: str = Field(default="", description="Department. Leave empty for demo default.")


class CheckUserApplicationAccessInput(BaseModel):
    employee_id: str = Field(default="", description="Employee ID. Leave empty for demo default (E001).")
    application_name: str = Field(default="", description="Application name. Leave empty for all affected apps.")


class CheckAuthenticationIssueInput(BaseModel):
    employee_id: str = Field(default="", description="Employee ID. Leave empty for demo default (E001).")
    office: str = Field(default="", description="Office. Leave empty for demo default (Hyderabad).")


class GetITTicketStatusInput(BaseModel):
    employee_id: str = Field(default="", description="Employee ID. Leave empty for demo default (E001).")
    ticket_id: str = Field(default="", description="Specific ticket ID (e.g., 'IT001'). Leave empty for all employee tickets.")


class GetITTicketAssigneeInput(BaseModel):
    employee_id: str = Field(default="", description="Employee ID. Leave empty for demo default (E001).")
    ticket_id: str = Field(default="", description="Specific ticket ID. Leave empty for all employee tickets.")


class GetITTicketLastUpdatedInput(BaseModel):
    employee_id: str = Field(default="", description="Employee ID. Leave empty for demo default (E001).")
    ticket_id: str = Field(default="", description="Specific ticket ID. Leave empty for all employee tickets.")


class FindRelatedIncidentInput(BaseModel):
    employee_id: str = Field(default="", description="Employee ID. Leave empty for demo default (E001).")
    issue_description: str = Field(default="", description="Optional description of the issue for context.")


class CreateITTicketInput(BaseModel):
    employee_id: str = Field(default="", description="Employee ID. Leave empty for demo default (E001).")
    employee_name: str = Field(default="", description="Employee name. Leave empty for demo default (Alice Johnson).")
    department: str = Field(default="", description="Department. Leave empty for demo default (AI).")
    issue_title: str = Field(default="", description="Brief title for the issue.")
    issue_description: str = Field(default="", description="Detailed description of the issue.")
    priority: str = Field(default="", description="Priority: 'Low', 'Medium', 'High', 'Critical'. Defaults to 'Medium'.")


class GetTeamIncidentsInput(BaseModel):
    manager_department: str = Field(default="", description="Manager's department. Leave empty for demo default (AI).")
    manager_id: str = Field(default="", description="Manager employee ID. Leave empty for demo default (E011).")


class GetTeamAffectedUsersInput(BaseModel):
    manager_department: str = Field(default="", description="Manager's department. Leave empty for demo default (AI).")
    incident_id: str = Field(default="", description="Specific incident ID. Leave empty for all active incidents.")


class CompareIncidentScopeInput(BaseModel):
    manager_department: str = Field(default="", description="Manager's department. Leave empty for demo default (AI).")
    incident_id: str = Field(default="", description="Specific incident ID. Leave empty for all active incidents.")


class GetIncidentStatusInput(BaseModel):
    incident_id: str = Field(default="", description="Specific incident ID. Leave empty for all active team incidents.")
    manager_department: str = Field(default="", description="Manager's department. Leave empty for demo default (AI).")


class GetIncidentOwnerInput(BaseModel):
    incident_id: str = Field(default="", description="Specific incident ID. Leave empty for all active team incidents.")
    manager_department: str = Field(default="", description="Manager's department. Leave empty for demo default (AI).")


class GetIncidentTimelineInput(BaseModel):
    incident_id: str = Field(default="", description="Specific incident ID. Leave empty for all active team incidents.")
    manager_department: str = Field(default="", description="Manager's department. Leave empty for demo default (AI).")


class GetIncidentETAInput(BaseModel):
    incident_id: str = Field(default="", description="Specific incident ID. Leave empty for all active team incidents.")
    manager_department: str = Field(default="", description="Manager's department. Leave empty for demo default (AI).")


class GetTeamUnresolvedTicketsInput(BaseModel):
    manager_department: str = Field(default="", description="Manager's department. Leave empty for demo default (AI).")


class GetRecurringTeamIncidentsInput(BaseModel):
    manager_department: str = Field(default="", description="Manager's department. Leave empty for demo default (AI).")


class EscalateIncidentInput(BaseModel):
    incident_id: str = Field(default="", description="Incident to escalate. Leave empty to auto-select most critical.")
    manager_id: str = Field(default="", description="Manager employee ID. Leave empty for demo default (E011).")
    manager_department: str = Field(default="", description="Manager's department. Leave empty for demo default (AI).")
    reason: str = Field(default="", description="Reason for escalation.")


class GetActiveIncidentsInput(BaseModel):
    pass  # no parameters needed


class GetCriticalServiceStatusInput(BaseModel):
    pass


class GetAffectedOfficesDepartmentsInput(BaseModel):
    pass


class GetIncidentImpactInput(BaseModel):
    pass


class GetIncidentUpdatesInput(BaseModel):
    pass


class GetIncidentResponsibleTeamInput(BaseModel):
    pass


class GetSLABreachesInput(BaseModel):
    pass


class GetRecurringIncidentsInput(BaseModel):
    pass


class FindDuplicateIncidentsInput(BaseModel):
    pass


class GetIncidentsRequiringEscalationInput(BaseModel):
    pass


# ===========================================================================
# MCPClient
# ===========================================================================

class MCPClient:
    """
    Client that dispatches tool calls to MCP tool functions.

    In DEMO_MODE, wraps the tool functions directly (same process).
    """

    def __init__(self):
        self.demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
        self._tools = self._load_tools()
        logger.info(
            "MCPClient initialized. DEMO_MODE=%s. Tools: %s",
            self.demo_mode,
            [t.name for t in self._tools],
        )

    def _load_tools(self) -> list[StructuredTool]:
        if self.demo_mode:
            from mcp_server.tools import (
                get_employee_info as _emp,
                get_department_info as _dept,
                get_project_info as _proj,
                search_company_policy as _pol,
                get_leave_balance as _leave_bal,
                get_hr_info as _hr_info,
                get_team_leave_info as _team_leave,
                get_team_attendance as _team_attendance,
                get_team_utilization as _team_util,
                admin_manage_user as _admin_user,
                get_compliance_training_status as _compliance,
                get_login_activity as _login,
                audit_login_activity as _audit_login,
                get_headcount_report as _headcount_report,
                get_admin_permissions as _admin_perms,
                # IT support — employee
                check_active_incidents as _check_active_incidents,
                check_application_status as _check_app_status,
                check_vpn_status as _check_vpn,
                check_network_status as _check_network,
                check_user_application_access as _check_user_app_access,
                check_authentication_issue as _check_auth_issue,
                get_it_ticket_status as _get_ticket_status,
                get_it_ticket_assignee as _get_ticket_assignee,
                get_it_ticket_last_updated as _get_ticket_updated,
                find_related_incident as _find_related_incident,
                create_it_ticket as _create_it_ticket,
                # IT support — manager
                get_team_incidents as _get_team_incidents,
                get_team_affected_users as _get_team_affected,
                compare_incident_scope as _compare_scope,
                get_incident_status as _get_incident_status,
                get_incident_owner as _get_incident_owner,
                get_incident_timeline as _get_incident_timeline,
                get_incident_eta as _get_incident_eta,
                get_team_unresolved_tickets as _get_team_unresolved,
                get_recurring_team_incidents as _get_recurring_team,
                escalate_incident as _escalate_incident,
                # IT support — admin
                get_active_incidents as _get_active_incidents,
                get_critical_service_status as _get_critical_svc,
                get_affected_offices_departments as _get_affected_offices,
                get_incident_impact as _get_incident_impact,
                get_incident_updates as _get_incident_updates,
                get_incident_responsible_team as _get_responsible_team,
                get_sla_breaches as _get_sla_breaches,
                get_recurring_incidents as _get_recurring_incidents,
                find_duplicate_incidents as _find_duplicates,
                get_incidents_requiring_escalation as _get_needs_escalation,
            )
            from mcp_server.permissions import permission_check_result, get_visible_fields, is_valid_role

            def get_employee_info(department: str = "", employee_id: str = "", user_role: str = "employee") -> str:
                if not is_valid_role(user_role):
                    return json.dumps({"error": f"Invalid user_role '{user_role}'"})
                visible = get_visible_fields(user_role)
                result = _emp(
                    department=department if department else None,
                    employee_id=employee_id if employee_id else None,
                    visible_fields=visible,
                )
                return json.dumps(result)

            def get_department_info(department_name: str = "") -> str:
                result = _dept(department_name=department_name if department_name else None)
                return json.dumps(result)

            def get_project_info(project_id: str = "", department: str = "", status: str = "") -> str:
                result = _proj(
                    project_id=project_id if project_id else None,
                    department=department if department else None,
                    status=status if status else None,
                )
                return json.dumps(result)

            def search_company_policy(query: str, document: str = "") -> str:
                if not query or not query.strip():
                    return json.dumps({"error": "query cannot be empty"})
                result = _pol(query=query, document=document if document else None)
                return json.dumps(result)

            def check_user_permission(role: str, tool_name: str) -> str:
                result = permission_check_result(role, tool_name)
                return json.dumps(result)

            def get_leave_balance(employee_id: str = "", employee_name: str = "", department: str = "") -> str:
                result = _leave_bal(
                    employee_id=employee_id if employee_id else None,
                    employee_name=employee_name if employee_name else None,
                    department=department if department else None,
                )
                return json.dumps(result)

            def get_hr_info(info_type: str, department: str = "", month: str = "", year: str = "") -> str:
                result = _hr_info(
                    info_type=info_type,
                    department=department if department else None,
                    month=month if month else None,
                    year=year if year else None,
                )
                return json.dumps(result)

            def get_team_leave_info(manager_department: str = "", info_type: str = "pending") -> str:
                result = _team_leave(
                    manager_department=manager_department if manager_department else None,
                    info_type=info_type,
                )
                return json.dumps(result)

            def get_team_attendance(department: str = "", month: str = "", year: str = "") -> str:
                result = _team_attendance(
                    department=department if department else None,
                    month=month if month else None,
                    year=year if year else None,
                )
                return json.dumps(result)

            def get_team_utilization(department: str = "") -> str:
                result = _team_util(department=department if department else None)
                return json.dumps(result)

            def admin_manage_user(action: str, employee_id: str = "", employee_name: str = "", department: str = "") -> str:
                result = _admin_user(
                    action=action,
                    employee_id=employee_id if employee_id else None,
                    employee_name=employee_name if employee_name else None,
                    department=department if department else None,
                )
                return json.dumps(result)

            def get_compliance_training_status(employee_id: str = "", department: str = "", status_filter: str = "") -> str:
                result = _compliance(
                    employee_id=employee_id if employee_id else None,
                    department=department if department else None,
                    status_filter=status_filter if status_filter else None,
                )
                return json.dumps(result)

            def get_login_activity(employee_id: str = "", employee_name: str = "", username: str = "", limit: int = 10) -> str:
                result = _login(
                    employee_id=employee_id if employee_id else None,
                    employee_name=employee_name if employee_name else None,
                    username=username if username else None,
                    limit=limit,
                )
                return json.dumps(result)

            def audit_login_activity(employee_id: str = "", employee_name: str = "", limit: int = 10) -> str:
                result = _audit_login(
                    employee_id=employee_id if employee_id else None,
                    employee_name=employee_name if employee_name else None,
                    limit=limit,
                )
                return json.dumps(result)

            def get_headcount_report(department: str = "") -> str:
                result = _headcount_report(
                    department=department if department else None,
                )
                return json.dumps(result)

            def get_admin_permissions(employee_id: str = "", permission_level: str = "") -> str:
                result = _admin_perms(
                    employee_id=employee_id if employee_id else None,
                    permission_level=permission_level if permission_level else None,
                )
                return json.dumps(result)

            # ── IT Support — Employee ─────────────────────────────────────

            def check_active_incidents(employee_id: str = "", department: str = "", office: str = "") -> str:
                result = _check_active_incidents(
                    employee_id=employee_id if employee_id else None,
                    department=department if department else None,
                    office=office if office else None,
                )
                return json.dumps(result)

            def check_application_status(application_name: str = "", department: str = "") -> str:
                result = _check_app_status(
                    application_name=application_name if application_name else None,
                    department=department if department else None,
                )
                return json.dumps(result)

            def check_vpn_status() -> str:
                return json.dumps(_check_vpn())

            def check_network_status(office: str = "", department: str = "") -> str:
                result = _check_network(
                    office=office if office else None,
                    department=department if department else None,
                )
                return json.dumps(result)

            def check_user_application_access(employee_id: str = "", application_name: str = "") -> str:
                result = _check_user_app_access(
                    employee_id=employee_id if employee_id else None,
                    application_name=application_name if application_name else None,
                )
                return json.dumps(result)

            def check_authentication_issue(employee_id: str = "", office: str = "") -> str:
                result = _check_auth_issue(
                    employee_id=employee_id if employee_id else None,
                    office=office if office else None,
                )
                return json.dumps(result)

            def get_it_ticket_status(employee_id: str = "", ticket_id: str = "") -> str:
                result = _get_ticket_status(
                    employee_id=employee_id if employee_id else None,
                    ticket_id=ticket_id if ticket_id else None,
                )
                return json.dumps(result)

            def get_it_ticket_assignee(employee_id: str = "", ticket_id: str = "") -> str:
                result = _get_ticket_assignee(
                    employee_id=employee_id if employee_id else None,
                    ticket_id=ticket_id if ticket_id else None,
                )
                return json.dumps(result)

            def get_it_ticket_last_updated(employee_id: str = "", ticket_id: str = "") -> str:
                result = _get_ticket_updated(
                    employee_id=employee_id if employee_id else None,
                    ticket_id=ticket_id if ticket_id else None,
                )
                return json.dumps(result)

            def find_related_incident(employee_id: str = "", issue_description: str = "") -> str:
                result = _find_related_incident(
                    employee_id=employee_id if employee_id else None,
                    issue_description=issue_description if issue_description else None,
                )
                return json.dumps(result)

            def create_it_ticket(
                employee_id: str = "", employee_name: str = "", department: str = "",
                issue_title: str = "", issue_description: str = "", priority: str = "",
            ) -> str:
                result = _create_it_ticket(
                    employee_id=employee_id if employee_id else None,
                    employee_name=employee_name if employee_name else None,
                    department=department if department else None,
                    issue_title=issue_title if issue_title else None,
                    issue_description=issue_description if issue_description else None,
                    priority=priority if priority else None,
                )
                return json.dumps(result)

            # ── IT Support — Manager ──────────────────────────────────────

            def get_team_incidents(manager_department: str = "", manager_id: str = "") -> str:
                result = _get_team_incidents(
                    manager_department=manager_department if manager_department else None,
                    manager_id=manager_id if manager_id else None,
                )
                return json.dumps(result)

            def get_team_affected_users(manager_department: str = "", incident_id: str = "") -> str:
                result = _get_team_affected(
                    manager_department=manager_department if manager_department else None,
                    incident_id=incident_id if incident_id else None,
                )
                return json.dumps(result)

            def compare_incident_scope(manager_department: str = "", incident_id: str = "") -> str:
                result = _compare_scope(
                    manager_department=manager_department if manager_department else None,
                    incident_id=incident_id if incident_id else None,
                )
                return json.dumps(result)

            def get_incident_status(incident_id: str = "", manager_department: str = "") -> str:
                result = _get_incident_status(
                    incident_id=incident_id if incident_id else None,
                    manager_department=manager_department if manager_department else None,
                )
                return json.dumps(result)

            def get_incident_owner(incident_id: str = "", manager_department: str = "") -> str:
                result = _get_incident_owner(
                    incident_id=incident_id if incident_id else None,
                    manager_department=manager_department if manager_department else None,
                )
                return json.dumps(result)

            def get_incident_timeline(incident_id: str = "", manager_department: str = "") -> str:
                result = _get_incident_timeline(
                    incident_id=incident_id if incident_id else None,
                    manager_department=manager_department if manager_department else None,
                )
                return json.dumps(result)

            def get_incident_eta(incident_id: str = "", manager_department: str = "") -> str:
                result = _get_incident_eta(
                    incident_id=incident_id if incident_id else None,
                    manager_department=manager_department if manager_department else None,
                )
                return json.dumps(result)

            def get_team_unresolved_tickets(manager_department: str = "") -> str:
                result = _get_team_unresolved(
                    manager_department=manager_department if manager_department else None,
                )
                return json.dumps(result)

            def get_recurring_team_incidents(manager_department: str = "") -> str:
                result = _get_recurring_team(
                    manager_department=manager_department if manager_department else None,
                )
                return json.dumps(result)

            def escalate_incident(
                incident_id: str = "", manager_id: str = "",
                manager_department: str = "", reason: str = "",
            ) -> str:
                result = _escalate_incident(
                    incident_id=incident_id if incident_id else None,
                    manager_id=manager_id if manager_id else None,
                    manager_department=manager_department if manager_department else None,
                    reason=reason if reason else None,
                )
                return json.dumps(result)

            # ── IT Support — Admin ────────────────────────────────────────

            def get_active_incidents() -> str:
                return json.dumps(_get_active_incidents())

            def get_critical_service_status() -> str:
                return json.dumps(_get_critical_svc())

            def get_affected_offices_departments() -> str:
                return json.dumps(_get_affected_offices())

            def get_incident_impact() -> str:
                return json.dumps(_get_incident_impact())

            def get_incident_updates() -> str:
                return json.dumps(_get_incident_updates())

            def get_incident_responsible_team() -> str:
                return json.dumps(_get_responsible_team())

            def get_sla_breaches() -> str:
                return json.dumps(_get_sla_breaches())

            def get_recurring_incidents() -> str:
                return json.dumps(_get_recurring_incidents())

            def find_duplicate_incidents() -> str:
                return json.dumps(_find_duplicates())

            def get_incidents_requiring_escalation() -> str:
                return json.dumps(_get_needs_escalation())

        else:
            raise NotImplementedError(
                "Non-demo MCP transport is not yet implemented. Set DEMO_MODE=true."
            )

        tools = [
            # ── Existing tools ─────────────────────────────────────────────
            StructuredTool.from_function(
                func=get_employee_info,
                name="get_employee_info",
                description="Get information about ACME Technologies employees. Filter by department or employee ID.",
                args_schema=GetEmployeeInfoInput,
            ),
            StructuredTool.from_function(
                func=get_department_info,
                name="get_department_info",
                description="Get information about ACME Technologies departments. Returns name, manager, description.",
                args_schema=GetDepartmentInfoInput,
            ),
            StructuredTool.from_function(
                func=get_project_info,
                name="get_project_info",
                description="Get information about ACME Technologies projects. Filter by ID, department, or status.",
                args_schema=GetProjectInfoInput,
            ),
            StructuredTool.from_function(
                func=search_company_policy,
                name="search_company_policy",
                description=(
                    "Search company policy documents for information about rules, "
                    "leave entitlements, resignation notice period, probation policy, "
                    "salary certificate process, reimbursement, overtime, headcount, "
                    "offboarding, onboarding, account restoration, and security requirements. "
                    "Use this for any HR policy or procedure question."
                ),
                args_schema=SearchCompanyPolicyInput,
            ),
            StructuredTool.from_function(
                func=check_user_permission,
                name="check_user_permission",
                description="Check whether a user role is permitted to call a specific tool.",
                args_schema=CheckUserPermissionInput,
            ),
            # ── Employee self-service tools ────────────────────────────────
            StructuredTool.from_function(
                func=get_leave_balance,
                name="get_leave_balance",
                description=(
                    "Get leave balance (annual, sick, casual) for an employee. "
                    "Shows total, used, and remaining days."
                ),
                args_schema=GetLeaveBalanceInput,
            ),
            StructuredTool.from_function(
                func=get_hr_info,
                name="get_hr_info",
                description=(
                    "Get HR information: HR contact for a department, "
                    "timesheet submission deadlines, or performance review schedule. "
                    "info_type must be one of: 'hr_contact', 'timesheet', 'performance'."
                ),
                args_schema=GetHRInfoInput,
            ),
            # ── Manager team tools ─────────────────────────────────────────
            StructuredTool.from_function(
                func=get_team_leave_info,
                name="get_team_leave_info",
                description=(
                    "Get leave information for a manager's team. "
                    "Use info_type='pending' for pending leave requests, "
                    "'upcoming' for team members on leave in the next two weeks, "
                    "'attendance' for the monthly attendance summary."
                ),
                args_schema=GetTeamLeaveInfoInput,
            ),
            StructuredTool.from_function(
                func=get_team_attendance,
                name="get_team_attendance",
                description=(
                    "Get the monthly attendance summary for a manager's team. "
                    "The demo manager is Karen Davis, AI department. "
                    "Call with department='AI' for demo context."
                ),
                args_schema=GetTeamAttendanceInput,
            ),
            StructuredTool.from_function(
                func=get_team_utilization,
                name="get_team_utilization",
                description=(
                    "Get team utilization rate across projects for a department. "
                    "Shows which employees are active on projects."
                ),
                args_schema=GetTeamUtilizationInput,
            ),
            # ── Admin tools ────────────────────────────────────────────────
            StructuredTool.from_function(
                func=admin_manage_user,
                name="admin_manage_user",
                description=(
                    "Perform administrative user management (DEMO MODE — simulated). "
                    "Actions: 'onboard', 'revoke_access', 'restore_account', "
                    "'headcount_report', 'get_accounts'."
                ),
                args_schema=AdminManageUserInput,
            ),
            StructuredTool.from_function(
                func=get_compliance_training_status,
                name="get_compliance_training_status",
                description="Get mandatory compliance training completion status.",
                args_schema=GetComplianceTrainingStatusInput,
            ),
            StructuredTool.from_function(
                func=get_login_activity,
                name="get_login_activity",
                description="Get login activity audit logs for a specific user.",
                args_schema=GetLoginActivityInput,
            ),
            StructuredTool.from_function(
                func=audit_login_activity,
                name="audit_login_activity",
                description=(
                    "Audit login activity for a specific user (Admin only). "
                    "Demo audit target is Alice Johnson (E001)."
                ),
                args_schema=AuditLoginActivityInput,
            ),
            StructuredTool.from_function(
                func=get_headcount_report,
                name="get_headcount_report",
                description=(
                    "Generate an organisation-wide headcount report across ALL departments (Admin only). "
                    "Leave department empty for the full org view."
                ),
                args_schema=GetHeadcountReportInput,
            ),
            StructuredTool.from_function(
                func=get_admin_permissions,
                name="get_admin_permissions",
                description="Get list of employees with admin or elevated permissions.",
                args_schema=GetAdminPermissionsInput,
            ),
            # ── IT Support — Employee tools ────────────────────────────────
            StructuredTool.from_function(
                func=check_active_incidents,
                name="check_active_incidents",
                description=(
                    "Check for active IT incidents affecting the employee's application or office. "
                    "Defaults to demo employee E001 (Alice Johnson, AI dept, Hyderabad). "
                    "Do NOT ask the user for their department or office."
                ),
                args_schema=CheckActiveIncidentsInput,
            ),
            StructuredTool.from_function(
                func=check_application_status,
                name="check_application_status",
                description=(
                    "Check the current status of a specific application or all company applications. "
                    "Use when an employee asks why they can't access an internal app."
                ),
                args_schema=CheckApplicationStatusInput,
            ),
            StructuredTool.from_function(
                func=check_vpn_status,
                name="check_vpn_status",
                description=(
                    "Check the current status of the company VPN. "
                    "Returns VPN health, affected users, and the related incident ID."
                ),
                args_schema=CheckVPNStatusInput,
            ),
            StructuredTool.from_function(
                func=check_network_status,
                name="check_network_status",
                description=(
                    "Check for network issues affecting the employee's office. "
                    "Defaults to Hyderabad office (demo employee context)."
                ),
                args_schema=CheckNetworkStatusInput,
            ),
            StructuredTool.from_function(
                func=check_user_application_access,
                name="check_user_application_access",
                description=(
                    "Diagnose why an employee cannot access an internal application. "
                    "Defaults to demo employee E001."
                ),
                args_schema=CheckUserApplicationAccessInput,
            ),
            StructuredTool.from_function(
                func=check_authentication_issue,
                name="check_authentication_issue",
                description=(
                    "Check whether the employee's login/authentication problem is a known company-wide issue. "
                    "Defaults to demo employee E001, Hyderabad."
                ),
                args_schema=CheckAuthenticationIssueInput,
            ),
            StructuredTool.from_function(
                func=get_it_ticket_status,
                name="get_it_ticket_status",
                description=(
                    "Get the current status of an employee's open IT ticket(s). "
                    "Defaults to demo employee E001 (Alice Johnson)."
                ),
                args_schema=GetITTicketStatusInput,
            ),
            StructuredTool.from_function(
                func=get_it_ticket_assignee,
                name="get_it_ticket_assignee",
                description=(
                    "Check whether an IT ticket has been assigned to a support engineer. "
                    "Defaults to demo employee E001."
                ),
                args_schema=GetITTicketAssigneeInput,
            ),
            StructuredTool.from_function(
                func=get_it_ticket_last_updated,
                name="get_it_ticket_last_updated",
                description=(
                    "Get the last-updated timestamp for an employee's IT ticket(s). "
                    "Defaults to demo employee E001."
                ),
                args_schema=GetITTicketLastUpdatedInput,
            ),
            StructuredTool.from_function(
                func=find_related_incident,
                name="find_related_incident",
                description=(
                    "Check whether an existing IT incident already covers the employee's problem. "
                    "Defaults to demo employee E001 (AI dept, Hyderabad)."
                ),
                args_schema=FindRelatedIncidentInput,
            ),
            StructuredTool.from_function(
                func=create_it_ticket,
                name="create_it_ticket",
                description=(
                    "Create a new IT support ticket for an employee (DEMO_MODE — simulated). "
                    "Defaults to demo employee E001 (Alice Johnson, AI, Hyderabad). "
                    "Returns a simulated ticket ID and confirmation."
                ),
                args_schema=CreateITTicketInput,
            ),
            # ── IT Support — Manager tools ─────────────────────────────────
            StructuredTool.from_function(
                func=get_team_incidents,
                name="get_team_incidents",
                description=(
                    "Return active IT incidents affecting a manager's team. "
                    "Defaults to demo manager Karen Davis (AI department). "
                    "Do NOT ask for department — use defaults."
                ),
                args_schema=GetTeamIncidentsInput,
            ),
            StructuredTool.from_function(
                func=get_team_affected_users,
                name="get_team_affected_users",
                description=(
                    "Return how many and which team members are affected by current IT incidents. "
                    "Defaults to demo manager Karen Davis (AI department)."
                ),
                args_schema=GetTeamAffectedUsersInput,
            ),
            StructuredTool.from_function(
                func=compare_incident_scope,
                name="compare_incident_scope",
                description=(
                    "Determine whether an incident is limited to the manager's team or is company-wide. "
                    "Defaults to demo manager Karen Davis (AI department)."
                ),
                args_schema=CompareIncidentScopeInput,
            ),
            StructuredTool.from_function(
                func=get_incident_status,
                name="get_incident_status",
                description=(
                    "Get the current status of IT incidents affecting a manager's team. "
                    "Defaults to demo manager Karen Davis (AI department)."
                ),
                args_schema=GetIncidentStatusInput,
            ),
            StructuredTool.from_function(
                func=get_incident_owner,
                name="get_incident_owner",
                description=(
                    "Identify which IT team is currently handling incidents for the manager's team. "
                    "Defaults to demo manager Karen Davis (AI department)."
                ),
                args_schema=GetIncidentOwnerInput,
            ),
            StructuredTool.from_function(
                func=get_incident_timeline,
                name="get_incident_timeline",
                description=(
                    "Get the timeline (reported_at and last_updated) for incidents affecting the manager's team. "
                    "Defaults to demo manager Karen Davis (AI department)."
                ),
                args_schema=GetIncidentTimelineInput,
            ),
            StructuredTool.from_function(
                func=get_incident_eta,
                name="get_incident_eta",
                description=(
                    "Get the estimated time to resolution (ETA) for active incidents affecting the manager's team. "
                    "Defaults to demo manager Karen Davis (AI department)."
                ),
                args_schema=GetIncidentETAInput,
            ),
            StructuredTool.from_function(
                func=get_team_unresolved_tickets,
                name="get_team_unresolved_tickets",
                description=(
                    "List team members who currently have unresolved IT tickets. "
                    "Defaults to demo manager Karen Davis (AI department team)."
                ),
                args_schema=GetTeamUnresolvedTicketsInput,
            ),
            StructuredTool.from_function(
                func=get_recurring_team_incidents,
                name="get_recurring_team_incidents",
                description=(
                    "Identify recurring IT problems affecting a manager's team by service. "
                    "Defaults to demo manager Karen Davis (AI department)."
                ),
                args_schema=GetRecurringTeamIncidentsInput,
            ),
            StructuredTool.from_function(
                func=escalate_incident,
                name="escalate_incident",
                description=(
                    "Simulate escalating a blocking IT incident on behalf of a manager (DEMO_MODE). "
                    "Defaults to demo manager Karen Davis (AI). "
                    "Auto-selects most critical open incident if none specified."
                ),
                args_schema=EscalateIncidentInput,
            ),
            # ── IT Support — Admin tools ───────────────────────────────────
            StructuredTool.from_function(
                func=get_active_incidents,
                name="get_active_incidents",
                description="Return all currently active IT incidents across the company (Admin only).",
                args_schema=GetActiveIncidentsInput,
            ),
            StructuredTool.from_function(
                func=get_critical_service_status,
                name="get_critical_service_status",
                description="Return the current status of all critical applications and services (Admin only).",
                args_schema=GetCriticalServiceStatusInput,
            ),
            StructuredTool.from_function(
                func=get_affected_offices_departments,
                name="get_affected_offices_departments",
                description="Return which offices and departments are experiencing IT issues (Admin only).",
                args_schema=GetAffectedOfficesDepartmentsInput,
            ),
            StructuredTool.from_function(
                func=get_incident_impact,
                name="get_incident_impact",
                description="Return user impact (affected_users count) per major active incident (Admin only).",
                args_schema=GetIncidentImpactInput,
            ),
            StructuredTool.from_function(
                func=get_incident_updates,
                name="get_incident_updates",
                description="Return the latest status and update timestamp for every active major incident (Admin only).",
                args_schema=GetIncidentUpdatesInput,
            ),
            StructuredTool.from_function(
                func=get_incident_responsible_team,
                name="get_incident_responsible_team",
                description="Return which IT team is responsible for resolving each active incident (Admin only).",
                args_schema=GetIncidentResponsibleTeamInput,
            ),
            StructuredTool.from_function(
                func=get_sla_breaches,
                name="get_sla_breaches",
                description="Identify incidents that have exceeded their SLA deadline (Admin only).",
                args_schema=GetSLABreachesInput,
            ),
            StructuredTool.from_function(
                func=get_recurring_incidents,
                name="get_recurring_incidents",
                description="Identify systems that have had multiple incidents recently (Admin only).",
                args_schema=GetRecurringIncidentsInput,
            ),
            StructuredTool.from_function(
                func=find_duplicate_incidents,
                name="find_duplicate_incidents",
                description="Identify potential duplicate incidents covering the same problem (Admin only).",
                args_schema=FindDuplicateIncidentsInput,
            ),
            StructuredTool.from_function(
                func=get_incidents_requiring_escalation,
                name="get_incidents_requiring_escalation",
                description="Identify active incidents requiring escalation or immediate attention (Admin only).",
                args_schema=GetIncidentsRequiringEscalationInput,
            ),
        ]
        return tools
    def get_tools(self) -> list[StructuredTool]:
        return self._tools

    def call_tool(self, tool_name: str, args: dict) -> str:
        tool_map = {t.name: t for t in self._tools}
        if tool_name not in tool_map:
            raise ValueError(
                f"Unknown tool '{tool_name}'. "
                f"Available tools: {list(tool_map.keys())}"
            )
        logger.debug("MCPClient.call_tool: %s(%s)", tool_name, args)
        return tool_map[tool_name].invoke(args)
