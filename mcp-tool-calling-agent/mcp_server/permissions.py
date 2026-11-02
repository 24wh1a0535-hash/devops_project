"""
permissions.py
--------------
Defines roles and what each role is allowed to do.

Roles:
    employee  - Can read general company info, departments, projects,
                own leave balance, HR contacts, timesheet deadlines,
                and company policies.
    manager   - Everything an employee can + team leave requests,
                attendance, utilization, performance reviews.
    admin     - Everything + all administrative tools (login auditing,
                compliance status, user management, permissions report).
"""

from typing import Optional

# ---- Role definitions -------------------------------------------------------

ROLES = ["employee", "manager", "admin"]

# Maps each role to the set of tools it may call
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "employee": [
        "get_department_info",
        "get_project_info",
        "get_employee_info",
        "search_company_policy",
        "check_user_permission",
        "get_leave_balance",
        "get_hr_info",
        # IT support — employee tools
        "check_active_incidents",
        "check_application_status",
        "check_vpn_status",
        "check_network_status",
        "check_user_application_access",
        "check_authentication_issue",
        "get_it_ticket_status",
        "get_it_ticket_assignee",
        "get_it_ticket_last_updated",
        "find_related_incident",
        "create_it_ticket",
    ],
    "manager": [
        "get_department_info",
        "get_project_info",
        "get_employee_info",
        "search_company_policy",
        "check_user_permission",
        "get_leave_balance",
        "get_hr_info",
        "get_team_leave_info",
        "get_team_utilization",
        "get_team_attendance",
        # IT support — employee tools (managers can also use employee-level tools)
        "check_active_incidents",
        "check_application_status",
        "check_vpn_status",
        "check_network_status",
        "check_user_application_access",
        "check_authentication_issue",
        "get_it_ticket_status",
        "get_it_ticket_assignee",
        "get_it_ticket_last_updated",
        "find_related_incident",
        "create_it_ticket",
        # IT support — manager tools
        "get_team_incidents",
        "get_team_affected_users",
        "compare_incident_scope",
        "get_incident_status",
        "get_incident_owner",
        "get_incident_timeline",
        "get_incident_eta",
        "get_team_unresolved_tickets",
        "get_recurring_team_incidents",
        "escalate_incident",
    ],
    "admin": [
        "get_department_info",
        "get_project_info",
        "get_employee_info",
        "search_company_policy",
        "check_user_permission",
        "get_leave_balance",
        "get_hr_info",
        "get_team_leave_info",
        "get_team_utilization",
        "get_team_attendance",
        "admin_manage_user",
        "get_compliance_training_status",
        "get_login_activity",
        "audit_login_activity",
        "get_headcount_report",
        "get_admin_permissions",
        "get_salary_info",
        # IT support — employee tools
        "check_active_incidents",
        "check_application_status",
        "check_vpn_status",
        "check_network_status",
        "check_user_application_access",
        "check_authentication_issue",
        "get_it_ticket_status",
        "get_it_ticket_assignee",
        "get_it_ticket_last_updated",
        "find_related_incident",
        "create_it_ticket",
        # IT support — manager tools
        "get_team_incidents",
        "get_team_affected_users",
        "compare_incident_scope",
        "get_incident_status",
        "get_incident_owner",
        "get_incident_timeline",
        "get_incident_eta",
        "get_team_unresolved_tickets",
        "get_recurring_team_incidents",
        "escalate_incident",
        # IT support — admin tools
        "get_active_incidents",
        "get_critical_service_status",
        "get_affected_offices_departments",
        "get_incident_impact",
        "get_incident_updates",
        "get_incident_responsible_team",
        "get_sla_breaches",
        "get_recurring_incidents",
        "find_duplicate_incidents",
        "get_incidents_requiring_escalation",
    ],
}

# Fields visible per role for employee data
EMPLOYEE_VISIBLE_FIELDS: dict[str, list[str]] = {
    "employee": ["employee_id", "name", "department", "role", "project_id"],
    "manager": ["employee_id", "name", "department", "role", "project_id", "access_level"],
    "admin":   ["employee_id", "name", "department", "role", "project_id", "access_level"],
}


# ---- Helper functions -------------------------------------------------------

def is_valid_role(role: str) -> bool:
    """Return True if the role string is one of the known roles."""
    return role.lower() in ROLES


def can_use_tool(role: str, tool_name: str) -> bool:
    """Return True if the given role is permitted to call the tool."""
    if not is_valid_role(role):
        return False
    return tool_name in ROLE_PERMISSIONS.get(role.lower(), [])


def get_visible_fields(role: str) -> list[str]:
    """Return the list of employee record fields visible to this role."""
    return EMPLOYEE_VISIBLE_FIELDS.get(role.lower(), EMPLOYEE_VISIBLE_FIELDS["employee"])


def permission_check_result(role: str, tool_name: str) -> dict:
    """
    Return a structured dict describing whether the role may call a tool.
    This is the response returned by the check_user_permission MCP tool.
    """
    if not is_valid_role(role):
        return {
            "allowed": False,
            "role": role,
            "tool": tool_name,
            "reason": f"Unknown role '{role}'. Valid roles: {ROLES}",
        }

    allowed = can_use_tool(role, tool_name)
    return {
        "allowed": allowed,
        "role": role.lower(),
        "tool": tool_name,
        "reason": "Access granted." if allowed else f"Role '{role}' is not permitted to call '{tool_name}'.",
    }
