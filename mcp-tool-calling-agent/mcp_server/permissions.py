"""
permissions.py
--------------
Defines roles and what each role is allowed to do.

Roles:
    employee  - Can read general company info, departments, projects
    manager   - Can read everything an employee can + detailed team info
    admin     - Can read everything
"""

from typing import Optional

# ---- Role definitions -------------------------------------------------------

ROLES = ["employee", "manager", "admin"]

# Maps each role to the set of tools it may call
ROLE_PERMISSIONS: dict[str, list[str]] = {
    "employee": [
        "get_department_info",
        "get_project_info",
        "get_employee_info",      # only public fields
        "search_company_policy",
        "check_user_permission",
    ],
    "manager": [
        "get_department_info",
        "get_project_info",
        "get_employee_info",
        "search_company_policy",
        "check_user_permission",
    ],
    "admin": [
        "get_department_info",
        "get_project_info",
        "get_employee_info",
        "search_company_policy",
        "check_user_permission",
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
