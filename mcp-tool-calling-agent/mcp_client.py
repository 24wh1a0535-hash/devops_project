"""
mcp_client.py
-------------
MCP Client: bridges the LangGraph agent and the MCP server.

The agent calls this client. The client calls the MCP server tools.
This keeps MCP as the transport layer between agent logic and data tools.

In DEMO_MODE (DEMO_MODE=true), the client calls the tool functions directly
in the same process (no network needed). This makes local development
and testing simple while preserving the MCP architecture.

When DEMO_MODE=false, the client would connect to an actual MCP server
process over stdio or HTTP (for Half 2 / production).
"""

import json
import logging
import os
from typing import Any

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ===========================================================================
# Pydantic input schemas for each tool
# These define the parameters the LLM sees and fills in.
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


# ===========================================================================
# MCPClient
# ===========================================================================

class MCPClient:
    """
    Client that dispatches tool calls to MCP tool functions.

    In DEMO_MODE, wraps the tool functions directly (same process).
    In non-demo mode, this class can be extended to use subprocess stdio
    or HTTP transport to a remote MCP server.
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
        """Build LangChain StructuredTool wrappers around each MCP tool function."""

        if self.demo_mode:
            # Import tool implementations directly (same process, no network)
            from mcp_server.tools import (
                get_employee_info as _emp,
                get_department_info as _dept,
                get_project_info as _proj,
                search_company_policy as _pol,
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

        else:
            raise NotImplementedError(
                "Non-demo MCP transport (stdio/HTTP to remote server) is "
                "not yet implemented. Set DEMO_MODE=true for local development."
            )

        tools = [
            StructuredTool.from_function(
                func=get_employee_info,
                name="get_employee_info",
                description=(
                    "Get information about ACME Technologies employees. "
                    "Filter by department name or employee ID. "
                    "Returns a list of employees with their role and project."
                ),
                args_schema=GetEmployeeInfoInput,
            ),
            StructuredTool.from_function(
                func=get_department_info,
                name="get_department_info",
                description=(
                    "Get information about ACME Technologies departments. "
                    "Returns department name, manager, and description. "
                    "Leave department_name empty to list all departments."
                ),
                args_schema=GetDepartmentInfoInput,
            ),
            StructuredTool.from_function(
                func=get_project_info,
                name="get_project_info",
                description=(
                    "Get information about ACME Technologies projects. "
                    "Filter by project ID, department, or status. "
                    "Returns project name, status, description, and team size."
                ),
                args_schema=GetProjectInfoInput,
            ),
            StructuredTool.from_function(
                func=search_company_policy,
                name="search_company_policy",
                description=(
                    "Search company policy documents for information about rules, "
                    "leave entitlements, security requirements, working hours, etc. "
                    "Provide keywords or a question as the query."
                ),
                args_schema=SearchCompanyPolicyInput,
            ),
            StructuredTool.from_function(
                func=check_user_permission,
                name="check_user_permission",
                description=(
                    "Check whether a user with a given role is permitted to call a tool. "
                    "Use this before accessing sensitive data to verify authorization."
                ),
                args_schema=CheckUserPermissionInput,
            ),
        ]
        return tools

    def get_tools(self) -> list[StructuredTool]:
        """Return the list of LangChain tool objects for binding to the LLM."""
        return self._tools

    def call_tool(self, tool_name: str, args: dict) -> str:
        """
        Call a tool by name with the given arguments.

        Args:
            tool_name: The name of the tool to call.
            args: A dict of arguments for the tool.

        Returns:
            JSON string with the tool result.

        Raises:
            ValueError: If the tool name is not found.
        """
        tool_map = {t.name: t for t in self._tools}
        if tool_name not in tool_map:
            raise ValueError(
                f"Unknown tool '{tool_name}'. "
                f"Available tools: {list(tool_map.keys())}"
            )
        logger.debug("MCPClient.call_tool: %s(%s)", tool_name, args)
        return tool_map[tool_name].invoke(args)
