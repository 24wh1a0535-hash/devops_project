"""
server.py
---------
MCP server for ACME Technologies internal data access.

Start this server before running the agent:
    python -m mcp_server.server

The server exposes tools via the Model Context Protocol (MCP):

Existing tools:
    - get_employee_info
    - get_department_info
    - get_project_info
    - search_company_policy
    - check_user_permission

Employee self-service tools:
    - get_leave_balance
    - get_hr_info

Manager team tools:
    - get_team_leave_info
    - get_team_utilization
    - get_team_attendance

Admin tools:
    - admin_manage_user
    - get_compliance_training_status
    - get_login_activity
    - audit_login_activity
    - get_headcount_report
    - get_admin_permissions

IT Support — Employee tools (10):
    - check_active_incidents
    - check_application_status
    - check_vpn_status
    - check_network_status
    - check_user_application_access
    - check_authentication_issue
    - get_it_ticket_status
    - get_it_ticket_assignee
    - get_it_ticket_last_updated
    - find_related_incident
    - create_it_ticket

IT Support — Manager tools (10):
    - get_team_incidents
    - get_team_affected_users
    - compare_incident_scope
    - get_incident_status
    - get_incident_owner
    - get_incident_timeline
    - get_incident_eta
    - get_team_unresolved_tickets
    - get_recurring_team_incidents
    - escalate_incident

IT Support — Admin tools (10):
    - get_active_incidents
    - get_critical_service_status
    - get_affected_offices_departments
    - get_incident_impact
    - get_incident_updates
    - get_incident_responsible_team
    - get_sla_breaches
    - get_recurring_incidents
    - find_duplicate_incidents
    - get_incidents_requiring_escalation
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.server.mcpserver import MCPServer as FastMCP
from mcp_server.tools import (
    get_employee_info as _get_employee_info,
    get_department_info as _get_department_info,
    get_project_info as _get_project_info,
    search_company_policy as _search_company_policy,
    get_leave_balance as _get_leave_balance,
    get_hr_info as _get_hr_info,
    get_team_leave_info as _get_team_leave_info,
    get_team_attendance as _get_team_attendance,
    get_team_utilization as _get_team_utilization,
    admin_manage_user as _admin_manage_user,
    get_compliance_training_status as _get_compliance_training_status,
    get_login_activity as _get_login_activity,
    audit_login_activity as _audit_login_activity,
    get_headcount_report as _get_headcount_report,
    get_admin_permissions as _get_admin_permissions,
    # IT support — employee
    check_active_incidents as _check_active_incidents,
    check_application_status as _check_application_status,
    check_vpn_status as _check_vpn_status,
    check_network_status as _check_network_status,
    check_user_application_access as _check_user_application_access,
    check_authentication_issue as _check_authentication_issue,
    get_it_ticket_status as _get_it_ticket_status,
    get_it_ticket_assignee as _get_it_ticket_assignee,
    get_it_ticket_last_updated as _get_it_ticket_last_updated,
    find_related_incident as _find_related_incident,
    create_it_ticket as _create_it_ticket,
    # IT support — manager
    get_team_incidents as _get_team_incidents,
    get_team_affected_users as _get_team_affected_users,
    compare_incident_scope as _compare_incident_scope,
    get_incident_status as _get_incident_status,
    get_incident_owner as _get_incident_owner,
    get_incident_timeline as _get_incident_timeline,
    get_incident_eta as _get_incident_eta,
    get_team_unresolved_tickets as _get_team_unresolved_tickets,
    get_recurring_team_incidents as _get_recurring_team_incidents,
    escalate_incident as _escalate_incident,
    # IT support — admin
    get_active_incidents as _get_active_incidents,
    get_critical_service_status as _get_critical_service_status,
    get_affected_offices_departments as _get_affected_offices_departments,
    get_incident_impact as _get_incident_impact,
    get_incident_updates as _get_incident_updates,
    get_incident_responsible_team as _get_incident_responsible_team,
    get_sla_breaches as _get_sla_breaches,
    get_recurring_incidents as _get_recurring_incidents,
    find_duplicate_incidents as _find_duplicate_incidents,
    get_incidents_requiring_escalation as _get_incidents_requiring_escalation,
)
from mcp_server.permissions import (
    permission_check_result,
    get_visible_fields,
    is_valid_role,
)

mcp = FastMCP(
    name="acme-company-data-server",
    instructions=(
        "You are a secure company data access server for ACME Technologies. "
        "You provide information about employees, departments, projects, "
        "company policies, leave, HR, IT incidents/tickets, and administrative data. "
        "Always check permissions before returning sensitive data."
    ),
)


# ── Existing tools ────────────────────────────────────────────────────────────

@mcp.tool()
def get_employee_info(
    department: str = "",
    employee_id: str = "",
    user_role: str = "employee",
) -> str:
    """
    Get information about employees.
    Filter by department name or employee ID.

    Args:
        department: Department name to filter (e.g., 'AI', 'Engineering'). Leave empty for all.
        employee_id: Specific employee ID (e.g., 'E001'). Leave empty for no ID filter.
        user_role: Role of requesting user ('employee', 'manager', 'admin'). Controls visible fields.
    """
    if not is_valid_role(user_role):
        return json.dumps({"error": f"Invalid user_role '{user_role}'. Use: employee, manager, admin"})
    visible = get_visible_fields(user_role)
    result = _get_employee_info(
        department=department if department else None,
        employee_id=employee_id if employee_id else None,
        visible_fields=visible,
    )
    return json.dumps(result)


@mcp.tool()
def get_department_info(department_name: str = "") -> str:
    """
    Get information about company departments.

    Args:
        department_name: Name of department to look up. Leave empty for all departments.
    """
    result = _get_department_info(department_name=department_name if department_name else None)
    return json.dumps(result)


@mcp.tool()
def get_project_info(
    project_id: str = "",
    department: str = "",
    status: str = "",
) -> str:
    """
    Get information about company projects.

    Args:
        project_id: Project ID (e.g., 'P001'). Leave empty to not filter.
        department: Filter by department. Leave empty for all.
        status: Filter by status: 'Active', 'Completed', 'In Progress'. Leave empty for all.
    """
    result = _get_project_info(
        project_id=project_id if project_id else None,
        department=department if department else None,
        status=status if status else None,
    )
    return json.dumps(result)


@mcp.tool()
def search_company_policy(query: str, document: str = "") -> str:
    """
    Search company policy documents for relevant information.

    Args:
        query: Search keywords or question.
        document: Optional. Specific document: 'company_policy', 'leave_policy', 'security_policy'.
    """
    if not query or not query.strip():
        return json.dumps({"error": "query cannot be empty"})
    result = _search_company_policy(query=query, document=document if document else None)
    return json.dumps(result)


@mcp.tool()
def check_user_permission(role: str, tool_name: str) -> str:
    """
    Check whether a user role is permitted to call a specific tool.

    Args:
        role: The user's role ('employee', 'manager', 'admin').
        tool_name: The name of the tool to check.
    """
    if not role or not role.strip():
        return json.dumps({"error": "role cannot be empty"})
    if not tool_name or not tool_name.strip():
        return json.dumps({"error": "tool_name cannot be empty"})
    result = permission_check_result(role.strip(), tool_name.strip())
    return json.dumps(result)


# ── Employee self-service tools ───────────────────────────────────────────────

@mcp.tool()
def get_leave_balance(
    employee_id: str = "",
    employee_name: str = "",
    department: str = "",
) -> str:
    """Get leave balance for an employee or department."""
    result = _get_leave_balance(
        employee_id=employee_id if employee_id else None,
        employee_name=employee_name if employee_name else None,
        department=department if department else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_hr_info(
    info_type: str,
    department: str = "",
    month: str = "",
    year: str = "",
) -> str:
    """Get HR-related information: HR contact, timesheet deadline, or performance review schedule."""
    result = _get_hr_info(
        info_type=info_type,
        department=department if department else None,
        month=month if month else None,
        year=year if year else None,
    )
    return json.dumps(result)


# ── Manager team tools ────────────────────────────────────────────────────────

@mcp.tool()
def get_team_leave_info(
    manager_department: str = "",
    info_type: str = "pending",
) -> str:
    """Get leave information for a manager's team."""
    result = _get_team_leave_info(
        manager_department=manager_department if manager_department else None,
        info_type=info_type,
    )
    return json.dumps(result)


@mcp.tool()
def get_team_attendance(
    department: str = "",
    month: str = "",
    year: str = "",
) -> str:
    """Get the monthly attendance summary for a manager's team."""
    result = _get_team_attendance(
        department=department if department else None,
        month=month if month else None,
        year=year if year else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_team_utilization(department: str = "") -> str:
    """Get team utilization rates across projects for a department."""
    result = _get_team_utilization(department=department if department else None)
    return json.dumps(result)


# ── Admin tools ───────────────────────────────────────────────────────────────

@mcp.tool()
def admin_manage_user(
    action: str,
    employee_id: str = "",
    employee_name: str = "",
    department: str = "",
) -> str:
    """Perform administrative user management actions (DEMO MODE — simulated)."""
    result = _admin_manage_user(
        action=action,
        employee_id=employee_id if employee_id else None,
        employee_name=employee_name if employee_name else None,
        department=department if department else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_compliance_training_status(
    employee_id: str = "",
    department: str = "",
    status_filter: str = "",
) -> str:
    """Get compliance training completion status for employees."""
    result = _get_compliance_training_status(
        employee_id=employee_id if employee_id else None,
        department=department if department else None,
        status_filter=status_filter if status_filter else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_login_activity(
    employee_id: str = "",
    employee_name: str = "",
    username: str = "",
    limit: int = 10,
) -> str:
    """Get login activity audit logs for a specific user."""
    result = _get_login_activity(
        employee_id=employee_id if employee_id else None,
        employee_name=employee_name if employee_name else None,
        username=username if username else None,
        limit=limit,
    )
    return json.dumps(result)


@mcp.tool()
def audit_login_activity(
    employee_id: str = "",
    employee_name: str = "",
    limit: int = 10,
) -> str:
    """Audit login activity for a specific user (Admin only). Defaults to Alice Johnson (E001)."""
    result = _audit_login_activity(
        employee_id=employee_id if employee_id else None,
        employee_name=employee_name if employee_name else None,
        limit=limit,
    )
    return json.dumps(result)


@mcp.tool()
def get_headcount_report(department: str = "") -> str:
    """Generate an organisation-wide headcount report across ALL departments (Admin only)."""
    result = _get_headcount_report(
        department=department if department else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_admin_permissions(
    employee_id: str = "",
    permission_level: str = "",
) -> str:
    """Get list of employees with admin or elevated permissions in the system."""
    result = _get_admin_permissions(
        employee_id=employee_id if employee_id else None,
        permission_level=permission_level if permission_level else None,
    )
    return json.dumps(result)


# ── IT Support — Employee tools ───────────────────────────────────────────────

@mcp.tool()
def check_active_incidents(
    employee_id: str = "",
    department: str = "",
    office: str = "",
) -> str:
    """
    Check for active IT incidents affecting the employee's application or office.
    Defaults to demo employee E001 (Alice Johnson, AI dept, Hyderabad).

    Args:
        employee_id: Employee ID. Leave empty to use demo default (E001).
        department: Department. Leave empty to use demo default (AI).
        office: Office. Leave empty to use demo default (Hyderabad).
    """
    result = _check_active_incidents(
        employee_id=employee_id if employee_id else None,
        department=department if department else None,
        office=office if office else None,
    )
    return json.dumps(result)


@mcp.tool()
def check_application_status(
    application_name: str = "",
    department: str = "",
) -> str:
    """
    Check the current status of a specific application or all company applications.

    Args:
        application_name: Application to check (e.g., 'SmartAssist AI Platform'). Leave empty for all affected.
        department: Department context. Leave empty to use demo default (AI).
    """
    result = _check_application_status(
        application_name=application_name if application_name else None,
        department=department if department else None,
    )
    return json.dumps(result)


@mcp.tool()
def check_vpn_status() -> str:
    """
    Check the current status of the company VPN.
    Returns VPN health, affected users, and the related incident ID.
    """
    result = _check_vpn_status()
    return json.dumps(result)


@mcp.tool()
def check_network_status(
    office: str = "",
    department: str = "",
) -> str:
    """
    Check for network issues affecting the employee's office.
    Defaults to Hyderabad office (demo employee context).

    Args:
        office: Office name or city. Leave empty to use demo default (Hyderabad).
        department: Department. Leave empty to use demo default.
    """
    result = _check_network_status(
        office=office if office else None,
        department=department if department else None,
    )
    return json.dumps(result)


@mcp.tool()
def check_user_application_access(
    employee_id: str = "",
    application_name: str = "",
) -> str:
    """
    Diagnose why an employee cannot access an internal application.
    Defaults to demo employee E001 (Alice Johnson).

    Args:
        employee_id: Employee ID. Leave empty to use demo default (E001).
        application_name: Application name. Leave empty for all affected apps.
    """
    result = _check_user_application_access(
        employee_id=employee_id if employee_id else None,
        application_name=application_name if application_name else None,
    )
    return json.dumps(result)


@mcp.tool()
def check_authentication_issue(
    employee_id: str = "",
    office: str = "",
) -> str:
    """
    Check whether the employee's login/authentication problem is a known issue.
    Defaults to demo employee E001, Hyderabad office.

    Args:
        employee_id: Employee ID. Leave empty to use demo default (E001).
        office: Office. Leave empty to use demo default (Hyderabad).
    """
    result = _check_authentication_issue(
        employee_id=employee_id if employee_id else None,
        office=office if office else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_it_ticket_status(
    employee_id: str = "",
    ticket_id: str = "",
) -> str:
    """
    Get the current status of an employee's open IT ticket(s).
    Defaults to demo employee E001 (Alice Johnson).

    Args:
        employee_id: Employee ID. Leave empty to use demo default (E001).
        ticket_id: Specific ticket ID (e.g., 'IT001'). Leave empty for all employee tickets.
    """
    result = _get_it_ticket_status(
        employee_id=employee_id if employee_id else None,
        ticket_id=ticket_id if ticket_id else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_it_ticket_assignee(
    employee_id: str = "",
    ticket_id: str = "",
) -> str:
    """
    Check whether an IT ticket has been assigned to a support engineer.
    Defaults to demo employee E001 (Alice Johnson).

    Args:
        employee_id: Employee ID. Leave empty to use demo default (E001).
        ticket_id: Specific ticket ID. Leave empty for all employee tickets.
    """
    result = _get_it_ticket_assignee(
        employee_id=employee_id if employee_id else None,
        ticket_id=ticket_id if ticket_id else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_it_ticket_last_updated(
    employee_id: str = "",
    ticket_id: str = "",
) -> str:
    """
    Get the last-updated timestamp for an employee's IT ticket(s).
    Defaults to demo employee E001 (Alice Johnson).

    Args:
        employee_id: Employee ID. Leave empty to use demo default (E001).
        ticket_id: Specific ticket ID. Leave empty for all employee tickets.
    """
    result = _get_it_ticket_last_updated(
        employee_id=employee_id if employee_id else None,
        ticket_id=ticket_id if ticket_id else None,
    )
    return json.dumps(result)


@mcp.tool()
def find_related_incident(
    employee_id: str = "",
    issue_description: str = "",
) -> str:
    """
    Check whether an existing IT incident already covers the employee's problem.
    Defaults to demo employee E001 (Alice Johnson, AI dept, Hyderabad).

    Args:
        employee_id: Employee ID. Leave empty to use demo default (E001).
        issue_description: Optional description of the issue for context.
    """
    result = _find_related_incident(
        employee_id=employee_id if employee_id else None,
        issue_description=issue_description if issue_description else None,
    )
    return json.dumps(result)


@mcp.tool()
def create_it_ticket(
    employee_id: str = "",
    employee_name: str = "",
    department: str = "",
    issue_title: str = "",
    issue_description: str = "",
    priority: str = "",
) -> str:
    """
    Create a new IT support ticket for an employee (DEMO_MODE — simulated).
    Defaults to demo employee E001 (Alice Johnson, AI, Hyderabad).

    Args:
        employee_id: Employee ID. Leave empty to use demo default (E001).
        employee_name: Employee name. Leave empty to use demo default (Alice Johnson).
        department: Department. Leave empty to use demo default (AI).
        issue_title: Brief title for the issue.
        issue_description: Detailed description of the issue.
        priority: Priority level: 'Low', 'Medium', 'High', 'Critical'. Defaults to 'Medium'.
    """
    result = _create_it_ticket(
        employee_id=employee_id if employee_id else None,
        employee_name=employee_name if employee_name else None,
        department=department if department else None,
        issue_title=issue_title if issue_title else None,
        issue_description=issue_description if issue_description else None,
        priority=priority if priority else None,
    )
    return json.dumps(result)


# ── IT Support — Manager tools ────────────────────────────────────────────────

@mcp.tool()
def get_team_incidents(
    manager_department: str = "",
    manager_id: str = "",
) -> str:
    """
    Return active IT incidents affecting a manager's team.
    Defaults to demo manager Karen Davis (AI department).

    Args:
        manager_department: Department. Leave empty to use demo default (AI).
        manager_id: Manager employee ID. Leave empty to use demo default (E011).
    """
    result = _get_team_incidents(
        manager_department=manager_department if manager_department else None,
        manager_id=manager_id if manager_id else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_team_affected_users(
    manager_department: str = "",
    incident_id: str = "",
) -> str:
    """
    Return how many and which team members are affected by current IT incidents.
    Defaults to demo manager Karen Davis (AI department).

    Args:
        manager_department: Department. Leave empty to use demo default (AI).
        incident_id: Specific incident ID. Leave empty for all active incidents.
    """
    result = _get_team_affected_users(
        manager_department=manager_department if manager_department else None,
        incident_id=incident_id if incident_id else None,
    )
    return json.dumps(result)


@mcp.tool()
def compare_incident_scope(
    manager_department: str = "",
    incident_id: str = "",
) -> str:
    """
    Determine whether an incident is limited to the manager's team or company-wide.
    Defaults to demo manager Karen Davis (AI department).

    Args:
        manager_department: Department. Leave empty to use demo default (AI).
        incident_id: Specific incident ID. Leave empty for all active incidents.
    """
    result = _compare_incident_scope(
        manager_department=manager_department if manager_department else None,
        incident_id=incident_id if incident_id else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_incident_status(
    incident_id: str = "",
    manager_department: str = "",
) -> str:
    """
    Get the current status of IT incidents affecting a manager's team.
    Defaults to demo manager Karen Davis (AI department).

    Args:
        incident_id: Specific incident ID. Leave empty for all active team incidents.
        manager_department: Department. Leave empty to use demo default (AI).
    """
    result = _get_incident_status(
        incident_id=incident_id if incident_id else None,
        manager_department=manager_department if manager_department else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_incident_owner(
    incident_id: str = "",
    manager_department: str = "",
) -> str:
    """
    Identify which IT team is currently handling active incidents for the manager's team.
    Defaults to demo manager Karen Davis (AI department).

    Args:
        incident_id: Specific incident ID. Leave empty for all active team incidents.
        manager_department: Department. Leave empty to use demo default (AI).
    """
    result = _get_incident_owner(
        incident_id=incident_id if incident_id else None,
        manager_department=manager_department if manager_department else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_incident_timeline(
    incident_id: str = "",
    manager_department: str = "",
) -> str:
    """
    Get the timeline (reported_at and last_updated) for incidents affecting the manager's team.
    Defaults to demo manager Karen Davis (AI department).

    Args:
        incident_id: Specific incident ID. Leave empty for all active team incidents.
        manager_department: Department. Leave empty to use demo default (AI).
    """
    result = _get_incident_timeline(
        incident_id=incident_id if incident_id else None,
        manager_department=manager_department if manager_department else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_incident_eta(
    incident_id: str = "",
    manager_department: str = "",
) -> str:
    """
    Get the estimated time to resolution (ETA) for active incidents affecting the manager's team.
    Defaults to demo manager Karen Davis (AI department).

    Args:
        incident_id: Specific incident ID. Leave empty for all active team incidents.
        manager_department: Department. Leave empty to use demo default (AI).
    """
    result = _get_incident_eta(
        incident_id=incident_id if incident_id else None,
        manager_department=manager_department if manager_department else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_team_unresolved_tickets(manager_department: str = "") -> str:
    """
    List team members who currently have unresolved IT tickets.
    Defaults to demo manager Karen Davis (AI department team members).

    Args:
        manager_department: Department. Leave empty to use demo default (AI).
    """
    result = _get_team_unresolved_tickets(
        manager_department=manager_department if manager_department else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_recurring_team_incidents(manager_department: str = "") -> str:
    """
    Identify recurring IT problems affecting a manager's team by service.
    Defaults to demo manager Karen Davis (AI department).

    Args:
        manager_department: Department. Leave empty to use demo default (AI).
    """
    result = _get_recurring_team_incidents(
        manager_department=manager_department if manager_department else None,
    )
    return json.dumps(result)


@mcp.tool()
def escalate_incident(
    incident_id: str = "",
    manager_id: str = "",
    manager_department: str = "",
    reason: str = "",
) -> str:
    """
    Simulate escalating a blocking IT incident on behalf of a manager (DEMO_MODE).
    Defaults to demo manager Karen Davis (AI department), most critical open incident.

    Args:
        incident_id: Specific incident to escalate. Leave empty to auto-select most critical.
        manager_id: Manager employee ID. Leave empty to use demo default (E011).
        manager_department: Department. Leave empty to use demo default (AI).
        reason: Reason for escalation. Leave empty for default reason.
    """
    result = _escalate_incident(
        incident_id=incident_id if incident_id else None,
        manager_id=manager_id if manager_id else None,
        manager_department=manager_department if manager_department else None,
        reason=reason if reason else None,
    )
    return json.dumps(result)


# ── IT Support — Admin tools ──────────────────────────────────────────────────

@mcp.tool()
def get_active_incidents() -> str:
    """
    Return all currently active IT incidents across the company (Admin only).
    """
    result = _get_active_incidents()
    return json.dumps(result)


@mcp.tool()
def get_critical_service_status() -> str:
    """
    Return the current status of all critical applications and services (Admin only).
    """
    result = _get_critical_service_status()
    return json.dumps(result)


@mcp.tool()
def get_affected_offices_departments() -> str:
    """
    Return a summary of which offices and departments are experiencing IT issues (Admin only).
    """
    result = _get_affected_offices_departments()
    return json.dumps(result)


@mcp.tool()
def get_incident_impact() -> str:
    """
    Return the user impact (affected_users count) for each major active incident (Admin only).
    """
    result = _get_incident_impact()
    return json.dumps(result)


@mcp.tool()
def get_incident_updates() -> str:
    """
    Return the latest status and update timestamp for every active major incident (Admin only).
    """
    result = _get_incident_updates()
    return json.dumps(result)


@mcp.tool()
def get_incident_responsible_team() -> str:
    """
    Return which team is responsible for resolving each active incident (Admin only).
    """
    result = _get_incident_responsible_team()
    return json.dumps(result)


@mcp.tool()
def get_sla_breaches() -> str:
    """
    Identify incidents that have exceeded their SLA deadline (Admin only).
    """
    result = _get_sla_breaches()
    return json.dumps(result)


@mcp.tool()
def get_recurring_incidents() -> str:
    """
    Identify systems that have had multiple incidents recently (Admin only).
    """
    result = _get_recurring_incidents()
    return json.dumps(result)


@mcp.tool()
def find_duplicate_incidents() -> str:
    """
    Identify potential duplicate incidents covering the same underlying problem (Admin only).
    """
    result = _find_duplicate_incidents()
    return json.dumps(result)


@mcp.tool()
def get_incidents_requiring_escalation() -> str:
    """
    Identify active incidents that require escalation or immediate attention (Admin only).
    """
    result = _get_incidents_requiring_escalation()
    return json.dumps(result)


# ---- Entry point ------------------------------------------------------------

if __name__ == "__main__":
    print("Starting ACME Technologies MCP Server...")
    print(
        "Tools: get_employee_info, get_department_info, get_project_info, "
        "search_company_policy, check_user_permission, get_leave_balance, "
        "get_hr_info, get_team_leave_info, get_team_attendance, get_team_utilization, "
        "admin_manage_user, get_compliance_training_status, "
        "get_login_activity, audit_login_activity, get_headcount_report, get_admin_permissions, "
        "check_active_incidents, check_application_status, check_vpn_status, "
        "check_network_status, check_user_application_access, check_authentication_issue, "
        "get_it_ticket_status, get_it_ticket_assignee, get_it_ticket_last_updated, "
        "find_related_incident, create_it_ticket, "
        "get_team_incidents, get_team_affected_users, compare_incident_scope, "
        "get_incident_status, get_incident_owner, get_incident_timeline, get_incident_eta, "
        "get_team_unresolved_tickets, get_recurring_team_incidents, escalate_incident, "
        "get_active_incidents, get_critical_service_status, get_affected_offices_departments, "
        "get_incident_impact, get_incident_updates, get_incident_responsible_team, "
        "get_sla_breaches, get_recurring_incidents, find_duplicate_incidents, "
        "get_incidents_requiring_escalation"
    )
    mcp.run(transport="stdio")

Start this server before running the agent:
    python -m mcp_server.server

The server exposes tools via the Model Context Protocol (MCP):

Existing tools:
    - get_employee_info
    - get_department_info
    - get_project_info
    - search_company_policy
    - check_user_permission

New tools (Employee self-service):
    - get_leave_balance
    - get_hr_info

New tools (Manager team tools):
    - get_team_leave_info
    - get_team_utilization

New tools (Admin tools):
    - admin_manage_user
    - get_compliance_training_status
    - get_login_activity
    - get_admin_permissions
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.server.mcpserver import MCPServer as FastMCP
from mcp_server.tools import (
    get_employee_info as _get_employee_info,
    get_department_info as _get_department_info,
    get_project_info as _get_project_info,
    search_company_policy as _search_company_policy,
    get_leave_balance as _get_leave_balance,
    get_hr_info as _get_hr_info,
    get_team_leave_info as _get_team_leave_info,
    get_team_attendance as _get_team_attendance,
    get_team_utilization as _get_team_utilization,
    admin_manage_user as _admin_manage_user,
    get_compliance_training_status as _get_compliance_training_status,
    get_login_activity as _get_login_activity,
    audit_login_activity as _audit_login_activity,
    get_headcount_report as _get_headcount_report,
    get_admin_permissions as _get_admin_permissions,
)
from mcp_server.permissions import (
    permission_check_result,
    get_visible_fields,
    is_valid_role,
)

mcp = FastMCP(
    name="acme-company-data-server",
    instructions=(
        "You are a secure company data access server for ACME Technologies. "
        "You provide information about employees, departments, projects, "
        "company policies, leave, HR, and administrative data. "
        "Always check permissions before returning sensitive data."
    ),
)


# ── Existing tools ────────────────────────────────────────────────────────────

@mcp.tool()
def get_employee_info(
    department: str = "",
    employee_id: str = "",
    user_role: str = "employee",
) -> str:
    """
    Get information about employees.
    Filter by department name or employee ID.
    Returns a list of employees matching the filter criteria.

    Args:
        department: Department name to filter (e.g., 'AI', 'Engineering'). Leave empty for all.
        employee_id: Specific employee ID (e.g., 'E001'). Leave empty for no ID filter.
        user_role: Role of requesting user ('employee', 'manager', 'admin'). Controls visible fields.
    """
    if not is_valid_role(user_role):
        return json.dumps({"error": f"Invalid user_role '{user_role}'. Use: employee, manager, admin"})
    visible = get_visible_fields(user_role)
    result = _get_employee_info(
        department=department if department else None,
        employee_id=employee_id if employee_id else None,
        visible_fields=visible,
    )
    return json.dumps(result)


@mcp.tool()
def get_department_info(department_name: str = "") -> str:
    """
    Get information about company departments.
    Returns department name, manager, and description.

    Args:
        department_name: Name of department to look up. Leave empty for all departments.
    """
    result = _get_department_info(department_name=department_name if department_name else None)
    return json.dumps(result)


@mcp.tool()
def get_project_info(
    project_id: str = "",
    department: str = "",
    status: str = "",
) -> str:
    """
    Get information about company projects.
    Filter by project ID, department, or status.

    Args:
        project_id: Project ID (e.g., 'P001'). Leave empty to not filter.
        department: Filter by department (e.g., 'AI'). Leave empty for all.
        status: Filter by status: 'Active', 'Completed', 'In Progress'. Leave empty for all.
    """
    result = _get_project_info(
        project_id=project_id if project_id else None,
        department=department if department else None,
        status=status if status else None,
    )
    return json.dumps(result)


@mcp.tool()
def search_company_policy(query: str, document: str = "") -> str:
    """
    Search company policy documents for relevant information.
    Use for HR policies, leave entitlements, security requirements,
    resignation, reimbursement, probation, onboarding, offboarding, etc.

    Args:
        query: Search keywords or question (e.g., 'notice period resign').
        document: Optional. Specific document: 'company_policy', 'leave_policy', 'security_policy'.
    """
    if not query or not query.strip():
        return json.dumps({"error": "query cannot be empty"})
    result = _search_company_policy(query=query, document=document if document else None)
    return json.dumps(result)


@mcp.tool()
def check_user_permission(role: str, tool_name: str) -> str:
    """
    Check whether a user role is permitted to call a specific tool.

    Args:
        role: The user's role ('employee', 'manager', 'admin').
        tool_name: The name of the tool to check.
    """
    if not role or not role.strip():
        return json.dumps({"error": "role cannot be empty"})
    if not tool_name or not tool_name.strip():
        return json.dumps({"error": "tool_name cannot be empty"})
    result = permission_check_result(role.strip(), tool_name.strip())
    return json.dumps(result)


# ── Employee self-service tools ───────────────────────────────────────────────

@mcp.tool()
def get_leave_balance(
    employee_id: str = "",
    employee_name: str = "",
    department: str = "",
) -> str:
    """
    Get leave balance for an employee or department.
    Returns annual, sick, and casual leave totals, used, and remaining days.

    Args:
        employee_id: Employee ID (e.g., 'E001'). Preferred for exact lookup.
        employee_name: Employee name (partial match). Use if ID not known.
        department: Filter by department. Leave empty to not filter by department.
    """
    result = _get_leave_balance(
        employee_id=employee_id if employee_id else None,
        employee_name=employee_name if employee_name else None,
        department=department if department else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_hr_info(
    info_type: str,
    department: str = "",
    month: str = "",
    year: str = "",
) -> str:
    """
    Get HR-related information: HR contact, timesheet deadline, or performance review schedule.

    Args:
        info_type: What to retrieve. Options:
                   'hr_contact'  - HR representative for a department
                   'timesheet'   - Timesheet submission deadline for a month/year
                   'performance' - Performance review schedule for a department
        department: Department name (for hr_contact and performance).
        month: Month name (e.g., 'October') for timesheet deadlines.
        year: Year (e.g., '2026') for timesheet deadlines.
    """
    result = _get_hr_info(
        info_type=info_type,
        department=department if department else None,
        month=month if month else None,
        year=year if year else None,
    )
    return json.dumps(result)


# ── Manager team tools ────────────────────────────────────────────────────────

@mcp.tool()
def get_team_leave_info(
    manager_department: str = "",
    info_type: str = "pending",
) -> str:
    """
    Get leave information for a manager's team.
    Use to check pending leave requests, upcoming leave, or attendance summary.

    Args:
        manager_department: The manager's department name (e.g., 'AI', 'Engineering').
        info_type: What to retrieve:
                   'pending'    - Pending leave requests awaiting approval
                   'upcoming'   - Team members on leave in the next two weeks
                   'attendance' - Monthly attendance summary for the team
    """
    result = _get_team_leave_info(
        manager_department=manager_department if manager_department else None,
        info_type=info_type,
    )
    return json.dumps(result)


@mcp.tool()
def get_team_attendance(
    department: str = "",
    month: str = "",
    year: str = "",
) -> str:
    """
    Get the monthly attendance summary for a manager's team.

    Use this tool when a manager asks about team attendance, attendance summary,
    or how their team attended this month. The manager's department is already
    known from context (AI department, managed by Karen Davis).

    Args:
        department: Department / team name (e.g., 'AI'). Defaults to 'AI' when empty.
        month:      Month name (e.g., 'September'). Leave empty to use available data.
        year:       Year (e.g., '2026'). Leave empty to use available data.
    """
    result = _get_team_attendance(
        department=department if department else None,
        month=month if month else None,
        year=year if year else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_team_utilization(department: str = "") -> str:
    """
    Get team utilization rates across projects for a department.
    Shows which employees are active on projects vs unassigned/completed.

    Args:
        department: Department name to filter (e.g., 'AI', 'Engineering'). Leave empty for all.
    """
    result = _get_team_utilization(department=department if department else None)
    return json.dumps(result)


# ── Admin tools ───────────────────────────────────────────────────────────────

@mcp.tool()
def admin_manage_user(
    action: str,
    employee_id: str = "",
    employee_name: str = "",
    department: str = "",
) -> str:
    """
    Perform administrative user management actions (DEMO MODE — simulated).
    Actions include onboarding, revoking access, restoring accounts, headcount reports.

    Args:
        action: The action to perform:
                'onboard'         - Show onboarding process steps for a new employee
                'revoke_access'   - Simulate revoking system access for a terminated employee
                'restore_account' - Simulate restoring a deactivated account
                'headcount_report'- Generate headcount report across departments
                'get_accounts'    - List user accounts in the system
        employee_id: Employee ID for user-specific actions.
        employee_name: Employee name for user-specific actions.
        department: Department filter for headcount or account listing.
    """
    result = _admin_manage_user(
        action=action,
        employee_id=employee_id if employee_id else None,
        employee_name=employee_name if employee_name else None,
        department=department if department else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_compliance_training_status(
    employee_id: str = "",
    department: str = "",
    status_filter: str = "",
) -> str:
    """
    Get compliance training completion status for employees.
    Returns employees who have not completed mandatory training courses.

    Args:
        employee_id: Filter by specific employee ID.
        department: Filter by department.
        status_filter: Filter by status: 'Not Started', 'In Progress', 'Completed'.
                       Leave empty to get all incomplete training (Not Started + In Progress).
    """
    result = _get_compliance_training_status(
        employee_id=employee_id if employee_id else None,
        department=department if department else None,
        status_filter=status_filter if status_filter else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_login_activity(
    employee_id: str = "",
    employee_name: str = "",
    username: str = "",
    limit: int = 10,
) -> str:
    """
    Get login activity audit logs for a specific user.
    Returns recent logins, logout times, IP addresses, devices, and failed attempts.

    Args:
        employee_id: Filter by employee ID.
        employee_name: Filter by employee name (partial match).
        username: Filter by system username.
        limit: Maximum number of log entries to return (default 10).
    """
    result = _get_login_activity(
        employee_id=employee_id if employee_id else None,
        employee_name=employee_name if employee_name else None,
        username=username if username else None,
        limit=limit,
    )
    return json.dumps(result)


@mcp.tool()
def audit_login_activity(
    employee_id: str = "",
    employee_name: str = "",
    limit: int = 10,
) -> str:
    """
    Audit login activity for a specific user (Admin only).

    Use this when an admin asks about auditing login activity for a specific user.
    The demo audit target is Alice Johnson (E001). Leave employee_id empty to use
    the default demo target — do NOT ask the user for an employee ID.

    Args:
        employee_id:   Employee ID to audit. Defaults to 'E001' (Alice Johnson).
        employee_name: Employee name override (partial match). Used only when employee_id is also set.
        limit:         Maximum number of log entries to return (default 10).
    """
    result = _audit_login_activity(
        employee_id=employee_id if employee_id else None,
        employee_name=employee_name if employee_name else None,
        limit=limit,
    )
    return json.dumps(result)


@mcp.tool()
def get_headcount_report(department: str = "") -> str:
    """
    Generate an organisation-wide headcount report across ALL departments (Admin only).

    Use this when an admin asks about headcount across all departments or the total
    number of employees per department. Leave department empty for the full
    organisation view.

    Args:
        department: Optional department filter (e.g., 'AI', 'Engineering').
                    Leave empty to get headcount across ALL departments.
    """
    result = _get_headcount_report(
        department=department if department else None,
    )
    return json.dumps(result)


@mcp.tool()
def get_admin_permissions(
    employee_id: str = "",
    permission_level: str = "",
) -> str:
    """
    Get list of employees with admin or elevated permissions in the system.

    Args:
        employee_id: Filter by specific employee. Leave empty to list all privileged accounts.
        permission_level: Filter by level: 'admin' or 'elevated'. Leave empty for all privileged accounts.
    """
    result = _get_admin_permissions(
        employee_id=employee_id if employee_id else None,
        permission_level=permission_level if permission_level else None,
    )
    return json.dumps(result)


# ---- Entry point ------------------------------------------------------------

if __name__ == "__main__":
    print("Starting ACME Technologies MCP Server...")
    print(
        "Tools: get_employee_info, get_department_info, get_project_info, "
        "search_company_policy, check_user_permission, get_leave_balance, "
        "get_hr_info, get_team_leave_info, get_team_attendance, get_team_utilization, "
        "admin_manage_user, get_compliance_training_status, "
        "get_login_activity, audit_login_activity, get_headcount_report, get_admin_permissions"
    )
    mcp.run(transport="stdio")
