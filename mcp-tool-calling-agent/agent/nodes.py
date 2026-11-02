"""
agent/nodes.py
--------------
Node functions for the LangGraph agent graph.

Nodes:
    call_llm_node   - Sends messages to the LLM; may call tools or respond directly.
    tool_node       - Executes MCP tool calls requested by the LLM.
"""

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage, SystemMessage

from agent.state import AgentState, ToolCallRecord
from agent.prompts import SYSTEM_PROMPT, TOOL_SELECTION_HINT
from mcp_server.permissions import can_use_tool

logger = logging.getLogger(__name__)

# All tools that require a role-based permission check before execution.
# This is the AUTHORITATIVE backend gate — independent of the UI question list.
PERMISSION_CHECKED_TOOLS = {
    # Existing tools
    "get_employee_info",
    "get_department_info",
    "get_project_info",
    "search_company_policy",
    # Employee tools
    "get_leave_balance",
    "get_hr_info",
    # Manager tools
    "get_team_leave_info",
    "get_team_attendance",
    "get_team_utilization",
    # Admin tools
    "admin_manage_user",
    "get_compliance_training_status",
    "get_login_activity",
    "audit_login_activity",
    "get_headcount_report",   # dedicated org-wide headcount report (Admin only)
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
}


def call_llm_node(state: AgentState, llm_with_tools) -> dict:
    """
    Send current message history to the LLM.

    Returns a state update with the AI response appended to messages.
    If the LLM returns a plain text answer (no tool calls) → final_answer is set.
    If the LLM requests tool calls → tool_node handles them next.
    """
    messages = state["messages"]

    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT + TOOL_SELECTION_HINT)] + list(messages)

    try:
        response: AIMessage = llm_with_tools.invoke(messages)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return {
            "messages": [],
            "error": f"LLM error: {str(e)}",
            "final_answer": None,
            "permission_denied": False,
        }

    if not response.tool_calls:
        return {
            "messages": [response],
            "final_answer": response.content,
            "error": None,
            "permission_denied": False,
        }

    return {
        "messages": [response],
        "final_answer": None,
        "error": None,
        "permission_denied": False,
    }


def tool_node(state: AgentState, mcp_client) -> dict:
    """
    Execute MCP tool calls from the last AI message.

    Checks permissions before each tool call.
    Returns ToolMessages with results, plus updated tool_results metadata.
    """
    messages = state["messages"]
    user_role = state.get("user_role", "employee")

    last_ai_message = None
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.tool_calls:
            last_ai_message = msg
            break

    if not last_ai_message:
        return {"messages": [], "tool_results": []}

    tool_messages = []
    tool_results: list[ToolCallRecord] = list(state.get("tool_results", []))
    any_denied = False

    for tool_call in last_ai_message.tool_calls:
        tool_name    = tool_call["name"]
        tool_args    = dict(tool_call["args"])
        tool_call_id = tool_call["id"]

        # ── Backend permission check ──────────────────────────────────────
        if tool_name in PERMISSION_CHECKED_TOOLS and not can_use_tool(user_role, tool_name):
            denied_msg = (
                "You do not have permission to access this information. "
                f"(Role '{user_role}' cannot call '{tool_name}'.)"
            )
            tool_messages.append(
                ToolMessage(
                    content=json.dumps({"error": denied_msg}),
                    tool_call_id=tool_call_id,
                    name=tool_name,
                )
            )
            tool_results.append(ToolCallRecord(
                tool=tool_name, args=tool_args,
                result=denied_msg, source="permission_denied",
                permission_ok=False,
            ))
            any_denied = True
            logger.warning("Permission denied: role=%s tool=%s", user_role, tool_name)
            continue

        # ── Inject user_role into tools that accept it ────────────────────
        if tool_name == "get_employee_info" and "user_role" not in tool_args:
            tool_args["user_role"] = user_role

        # ── Call the tool ─────────────────────────────────────────────────
        logger.info("Calling MCP tool: %s | args: %s | role: %s", tool_name, tool_args, user_role)
        try:
            raw = mcp_client.call_tool(tool_name, tool_args)
            result_str = raw if isinstance(raw, str) else json.dumps(raw)
        except Exception as e:
            logger.error("Tool call failed for %s: %s", tool_name, e)
            result_str = json.dumps({"error": f"Tool '{tool_name}' failed: {str(e)}"})

        try:
            parsed = json.loads(result_str)
            source = parsed.get("source", "unknown")
        except Exception:
            source = "unknown"

        tool_messages.append(
            ToolMessage(content=result_str, tool_call_id=tool_call_id, name=tool_name)
        )
        tool_results.append(ToolCallRecord(
            tool=tool_name, args=tool_args,
            result=result_str, source=source,
            permission_ok=True,
        ))

    return {
        "messages": tool_messages,
        "tool_results": tool_results,
        "permission_denied": any_denied,
    }
