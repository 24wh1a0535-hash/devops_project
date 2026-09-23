"""
server.py
---------
MCP server for ACME Technologies internal data access.

Start this server before running the agent:
    python -m mcp_server.server

The server exposes these tools via the Model Context Protocol (MCP):
    - get_employee_info
    - get_department_info
    - get_project_info
    - search_company_policy
    - check_user_permission
"""

import json
import os
import sys

# Allow running as a module from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp.server.mcpserver import MCPServer as FastMCP
from mcp_server.tools import (
    get_employee_info as _get_employee_info,
    get_department_info as _get_department_info,
    get_project_info as _get_project_info,
    search_company_policy as _search_company_policy,
)
from mcp_server.permissions import (
    permission_check_result,
    get_visible_fields,
    is_valid_role,
)

# ---- Create MCP server ------------------------------------------------------

mcp = FastMCP(
    name="acme-company-data-server",
    instructions=(
        "You are a secure company data access server for ACME Technologies. "
        "You provide information about employees, departments, projects, and "
        "company policies. Always check permissions before returning sensitive data."
    ),
)


# ---- Tool: get_employee_info ------------------------------------------------

@mcp.tool()
def get_employee_info(
    department: str = "",
    employee_id: str = "",
    user_role: str = "employee",
) -> str:
    """
    Get information about employees.

    Use this tool to find employees by department or by employee ID.
    Returns a list of employees matching the filter criteria.

    Args:
        department: Department name to filter employees (e.g., 'AI', 'Engineering').
                    Leave empty to not filter by department.
        employee_id: Specific employee ID (e.g., 'E001'). Leave empty to not filter by ID.
        user_role: The role of the requesting user ('employee', 'manager', 'admin').
                   Controls which fields are visible in the response.
    """
    # Validate role
    if not is_valid_role(user_role):
        return json.dumps({"error": f"Invalid user_role '{user_role}'. Use: employee, manager, admin"})

    # Determine which fields are visible for this role
    visible = get_visible_fields(user_role)

    result = _get_employee_info(
        department=department if department else None,
        employee_id=employee_id if employee_id else None,
        visible_fields=visible,
    )
    return json.dumps(result)


# ---- Tool: get_department_info ----------------------------------------------

@mcp.tool()
def get_department_info(department_name: str = "") -> str:
    """
    Get information about company departments.

    Use this tool to look up details about a specific department or
    list all departments. Returns department name, manager, and description.

    Args:
        department_name: Name of the department to look up (e.g., 'AI', 'Security').
                         Leave empty to get all departments.
    """
    result = _get_department_info(
        department_name=department_name if department_name else None
    )
    return json.dumps(result)


# ---- Tool: get_project_info -------------------------------------------------

@mcp.tool()
def get_project_info(
    project_id: str = "",
    department: str = "",
    status: str = "",
) -> str:
    """
    Get information about company projects.

    Use this tool to find projects by ID, department, or status.

    Args:
        project_id: Specific project ID (e.g., 'P001'). Leave empty to not filter.
        department: Filter projects by department (e.g., 'AI', 'Engineering').
                    Leave empty to not filter by department.
        status: Filter by status: 'Active', 'Completed', 'In Progress'.
                Leave empty to return all statuses.
    """
    result = _get_project_info(
        project_id=project_id if project_id else None,
        department=department if department else None,
        status=status if status else None,
    )
    return json.dumps(result)


# ---- Tool: search_company_policy --------------------------------------------

@mcp.tool()
def search_company_policy(
    query: str,
    document: str = "",
) -> str:
    """
    Search company policy documents for relevant information.

    Use this tool to answer questions about company rules, HR policies,
    leave entitlements, security requirements, and other official guidelines.

    Args:
        query: The search keywords or question (e.g., 'annual leave days',
               'password requirements', 'maternity leave').
        document: Optional. Specific document to search:
                  'company_policy', 'leave_policy', or 'security_policy'.
                  Leave empty to search all documents.
    """
    if not query or not query.strip():
        return json.dumps({"error": "query cannot be empty"})

    result = _search_company_policy(
        query=query,
        document=document if document else None,
    )
    return json.dumps(result)


# ---- Tool: check_user_permission --------------------------------------------

@mcp.tool()
def check_user_permission(role: str, tool_name: str) -> str:
    """
    Check whether a user role is permitted to call a specific tool.

    Use this tool before accessing sensitive data to verify authorization.

    Args:
        role: The user's role ('employee', 'manager', 'admin').
        tool_name: The name of the tool to check access for
                   (e.g., 'get_employee_info', 'get_department_info').
    """
    if not role or not role.strip():
        return json.dumps({"error": "role cannot be empty"})
    if not tool_name or not tool_name.strip():
        return json.dumps({"error": "tool_name cannot be empty"})

    result = permission_check_result(role.strip(), tool_name.strip())
    return json.dumps(result)


# ---- Entry point ------------------------------------------------------------

if __name__ == "__main__":
    print("Starting ACME Technologies MCP Server...")
    print("Tools available: get_employee_info, get_department_info, "
          "get_project_info, search_company_policy, check_user_permission")
    # Run using stdio transport (default for MCP)
    mcp.run(transport="stdio")
