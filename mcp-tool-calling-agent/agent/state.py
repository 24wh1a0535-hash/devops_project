"""
agent/state.py
--------------
Shared state object flowing through the LangGraph.
"""

from typing import Annotated, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages


class ToolCallRecord(TypedDict):
    """Metadata for one tool call made during a turn."""
    tool: str
    args: dict
    result: str
    source: str          # e.g. local_csv / databricks_unity_catalog / local_keyword_search
    permission_ok: bool


class AgentState(TypedDict):
    """
    Complete agent state at any point during a conversation.

    messages:        Full conversation history (user + AI + tool messages).
    user_role:       Role of the requesting user (employee/manager/admin).
    tool_results:    Metadata for each tool call made this turn.
    final_answer:    Final text answer to return to the user.
    error:           Error message to surface to the user.
    permission_denied: True if the last action was blocked by permissions.
    """
    messages: Annotated[list, add_messages]
    user_role: str
    tool_results: list[ToolCallRecord]
    final_answer: Optional[str]
    error: Optional[str]
    permission_denied: bool
