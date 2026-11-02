"""
role_questions.py
-----------------
Centralised mapping of user roles to the example questions that are
appropriate for that role.

Design
------
Employee has 10 questions; Manager has 10 questions; Admin has 10 questions.
30 questions total. No question appears in more than one role's list —
the lists are strictly exclusive.  The UI reads these lists and displays
ONLY the questions belonging to the currently selected role.

Security note
-------------
This module controls only the *UI display* of example questions.
The backend permission check in ``agent/nodes.py`` (``can_use_tool``) is
completely independent and remains the authoritative gate for every tool
call, regardless of what questions are visible in the sidebar.

Usage
-----
    from role_questions import get_questions_for_role, ALL_ROLES

    questions = get_questions_for_role("employee")  # → list[str], exactly 10 items
"""

from mcp_server.permissions import ROLES, can_use_tool

# ---------------------------------------------------------------------------
# Master role → question mapping
# Each role has exactly 10 questions. Lists are mutually exclusive.
# ---------------------------------------------------------------------------
ROLE_EXAMPLE_QUESTIONS: dict[str, list[str]] = {
    "employee": [
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
    ],
    "manager": [
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
    ],
    "admin": [
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
    ],
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_questions_for_role(role: str) -> list[str]:
    """
    Return the list of example questions for *role*.

    Parameters
    ----------
    role : str
        One of "employee", "manager", "admin" (case-insensitive).

    Returns
    -------
    list[str]
        Ordered list of exactly 10 question strings for the role.
        Returns an empty list for unknown / invalid roles.
    """
    role = role.lower().strip()
    return list(ROLE_EXAMPLE_QUESTIONS.get(role, []))


def get_all_roles() -> list[str]:
    """Return the canonical list of role names (from permissions module)."""
    return list(ROLES)


def get_catalogue() -> list[dict]:
    """
    Return a flat catalogue view of all questions (for test compatibility).

    Each entry has:
        "question" – the question text
        "roles"    – list containing only the single owning role
    """
    catalogue: list[dict] = []
    for role, questions in ROLE_EXAMPLE_QUESTIONS.items():
        for question in questions:
            catalogue.append({
                "question": question,
                "roles": [role],
                "required_tool": None,  # questions are UX only; no tool binding
            })
    return catalogue
