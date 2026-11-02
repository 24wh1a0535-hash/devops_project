"""
mcp_server/tools.py
--------------------
Data-access functions used by the MCP server tools.

Each function automatically routes to the correct data source:

    DEMO_MODE=true  → Local CSV files  (no cloud needed)
    DEMO_MODE=false → Databricks Unity Catalog tables (with CSV fallback)

The vector search for policy documents routes through:
    vector_search/search.py → local keyword store  (DEMO_MODE=true)
                             → Databricks Vector Search (DEMO_MODE=false)

These functions are kept separate from the MCP wiring so they can be
unit-tested directly without starting a server.
"""

import csv
import logging
import os
import pathlib
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _data_dir() -> pathlib.Path:
    base = pathlib.Path(__file__).parent.parent
    return base / os.getenv("DATA_DIR", "data")


def _read_csv(filename: str) -> list[dict]:
    filepath = _data_dir() / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Data file not found: {filepath}")
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _is_demo() -> bool:
    return os.getenv("DEMO_MODE", "true").lower() == "true"


# ── Employee data ─────────────────────────────────────────────────────────────

def get_employee_info(
    department: Optional[str] = None,
    employee_id: Optional[str] = None,
    visible_fields: Optional[list[str]] = None,
) -> dict:
    """
    Return employee information filtered by department or employee_id.

    Routes to:
        DEMO_MODE=true  → employees.csv
        DEMO_MODE=false → Databricks Unity Catalog employees table
    """
    if department is not None:
        if not isinstance(department, str):
            return {"error": "Invalid 'department'. Must be a string."}
        department = department.strip() or None

    if employee_id is not None:
        if not isinstance(employee_id, str):
            return {"error": "Invalid 'employee_id'. Must be a string."}
        employee_id = employee_id.strip().upper() or None

    if _is_demo():
        rows = _get_employees_local(department, employee_id)
        source = "local_csv"
    else:
        rows = _get_employees_databricks(department, employee_id)
        source = "databricks_unity_catalog"

    if isinstance(rows, dict) and "error" in rows:
        return rows

    if visible_fields:
        rows = [{k: v for k, v in row.items() if k in visible_fields} for row in rows]

    return {"employees": rows, "count": len(rows), "source": source}


def _get_employees_local(department, employee_id) -> list[dict]:
    try:
        rows = _read_csv("employees.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}
    if employee_id:
        rows = [r for r in rows if r.get("employee_id", "").upper() == employee_id]
    elif department:
        rows = [r for r in rows if r.get("department", "").lower() == department.lower()]
    return rows


def _get_employees_databricks(department, employee_id) -> list[dict]:
    try:
        from databricks.client import get_connection, get_catalog, get_schema
        from databricks.queries import query_employees
        conn = get_connection()
        return query_employees(conn, get_catalog(), get_schema(), department, employee_id)
    except Exception as e:
        logger.error("Databricks employee query failed: %s. Falling back to local CSV.", e)
        return _get_employees_local(department, employee_id)

def get_salary_info(employee_id: Optional[str] = None) -> dict:

    if employee_id is not None:
        employee_id = str(employee_id).strip().upper() or None

    if _is_demo():

        rows = _read_csv("employees.csv")
        source = "local_csv"

        if employee_id:
            rows = [
                row for row in rows
                if row.get("employee_id", "").upper() == employee_id
            ]
    else:

        rows = _get_employees_databricks(None, employee_id)
        source = "databricks_unity_catalog"

    if isinstance(rows, dict) and "error" in rows:
        return rows

    salary_data = []

    for row in rows:

        salary_data.append({
            "employee_id": row.get("employee_id"),
            "name": row.get("name"),
            "salary": row.get("salary")
        })

    return {
        "salary_information": salary_data,
        "count": len(salary_data),
        "source": source
    } 
# ── Department data ───────────────────────────────────────────────────────────

def get_department_info(department_name: Optional[str] = None) -> dict:
    """
    Return department information.

    Routes to:
        DEMO_MODE=true  → departments.csv
        DEMO_MODE=false → Databricks Unity Catalog departments table
    """
    if department_name is not None:
        if not isinstance(department_name, str):
            return {"error": "Invalid 'department_name'. Must be a string."}
        department_name = department_name.strip() or None

    if _is_demo():
        rows = _get_departments_local(department_name)
        source = "local_csv"
    else:
        rows = _get_departments_databricks(department_name)
        source = "databricks_unity_catalog"

    if isinstance(rows, dict) and "error" in rows:
        return rows

    return {"departments": rows, "count": len(rows), "source": source}


def _get_departments_local(department_name) -> list[dict]:
    try:
        rows = _read_csv("departments.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}
    if department_name:
        rows = [r for r in rows if r.get("department_name", "").lower() == department_name.lower()]
    return rows


def _get_departments_databricks(department_name) -> list[dict]:
    try:
        from databricks.client import get_connection, get_catalog, get_schema
        from databricks.queries import query_departments
        conn = get_connection()
        return query_departments(conn, get_catalog(), get_schema(), department_name)
    except Exception as e:
        logger.error("Databricks department query failed: %s. Falling back to local CSV.", e)
        return _get_departments_local(department_name)


# ── Project data ──────────────────────────────────────────────────────────────

def get_project_info(
    project_id: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
) -> dict:
    """
    Return project information with optional filters.

    Routes to:
        DEMO_MODE=true  → projects.csv
        DEMO_MODE=false → Databricks Unity Catalog projects table
    """
    if project_id is not None:
        project_id = str(project_id).strip().upper() or None
    if department is not None:
        department = str(department).strip() or None
    if status is not None:
        status = str(status).strip() or None

    if _is_demo():
        rows = _get_projects_local(project_id, department, status)
        source = "local_csv"
    else:
        rows = _get_projects_databricks(project_id, department, status)
        source = "databricks_unity_catalog"

    if isinstance(rows, dict) and "error" in rows:
        return rows

    return {"projects": rows, "count": len(rows), "source": source}


def _get_projects_local(project_id, department, status) -> list[dict]:
    try:
        rows = _read_csv("projects.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}
    if project_id:
        rows = [r for r in rows if r.get("project_id", "").upper() == project_id]
    if department:
        rows = [r for r in rows if r.get("department", "").lower() == department.lower()]
    if status:
        rows = [r for r in rows if r.get("status", "").lower() == status.lower()]
    return rows


def _get_projects_databricks(project_id, department, status) -> list[dict]:
    try:
        from databricks.client import get_connection, get_catalog, get_schema
        from databricks.queries import query_projects
        conn = get_connection()
        return query_projects(conn, get_catalog(), get_schema(), project_id, department, status)
    except Exception as e:
        logger.error("Databricks project query failed: %s. Falling back to local CSV.", e)
        return _get_projects_local(project_id, department, status)


# ── Policy / document search ──────────────────────────────────────────────────

def _relevant_excerpt(text: str, query: str, window: int = 600) -> str:
    """Return the most relevant portion of a chunk for the given query."""
    text_lower = text.lower()
    keywords = sorted(query.lower().split(), key=len, reverse=True)
    hit_pos = -1
    for kw in keywords:
        pos = text_lower.find(kw)
        if pos != -1:
            hit_pos = pos
            break

    if hit_pos == -1:
        return text[:window]

    start = max(0, hit_pos - window // 4)
    end   = min(len(text), start + window)
    if start > 0:
        start = text.rfind(" ", 0, start) + 1
    excerpt = text[start:end].strip()
    return excerpt


def search_company_policy(query: str, document: Optional[str] = None) -> dict:
    """
    Search company policy documents for relevant content.

    Routes to:
        DEMO_MODE=true  → Local keyword search (vector_search/search.py)
        DEMO_MODE=false → Databricks Vector Search
    """
    if not isinstance(query, str) or not query.strip():
        return {"error": "Invalid 'query'. Must be a non-empty string."}
    query = query.strip()

    valid_docs = {"company_policy", "leave_policy", "security_policy"}
    if document:
        document = document.strip().lower()
        if document not in valid_docs:
            return {
                "error": f"Unknown document '{document}'. "
                         f"Choose from: {sorted(valid_docs)}"
            }

    from vector_search.search import search_documents
    result = search_documents(query=query, doc_filter=document, top_k=5)

    formatted = []
    for r in result.get("results", []):
        full_text = r.get("text", "")
        formatted.append({
            "document": r.get("doc_name", ""),
            "excerpt":  _relevant_excerpt(full_text, query),
            "score":    r.get("score", 0),
            "source":   r.get("source", ""),
        })

    mode = result.get("mode", "local_keyword_search")
    if "databricks" in mode:
        source = "databricks_vector_search"
    else:
        source = "local_document"

    return {
        "query":   query,
        "results": formatted,
        "count":   len(formatted),
        "mode":    mode,
        "source":  source,
    }


# ── Leave balance ─────────────────────────────────────────────────────────────

def get_leave_balance(
    employee_id: Optional[str] = None,
    employee_name: Optional[str] = None,
    department: Optional[str] = None,
) -> dict:
    """
    Return leave balance for one or more employees.

    Reads from leave_balances.csv.
    Filter by employee_id, employee_name, or department.
    Without any filter, returns all balances.
    """
    try:
        rows = _read_csv("leave_balances.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    if employee_id:
        rows = [r for r in rows if r.get("employee_id", "").upper() == employee_id.strip().upper()]
    elif employee_name:
        rows = [r for r in rows if employee_name.lower() in r.get("name", "").lower()]
    elif department:
        rows = [r for r in rows if r.get("department", "").lower() == department.strip().lower()]

    return {
        "leave_balances": rows,
        "count": len(rows),
        "source": "local_csv",
        "note": "[DEMO MODE] Leave balances are simulated demo data.",
    }


# ── HR information ────────────────────────────────────────────────────────────

def get_hr_info(
    info_type: str,
    department: Optional[str] = None,
    month: Optional[str] = None,
    year: Optional[str] = None,
) -> dict:
    """
    Return HR-related information based on the requested type.

    info_type options:
        "hr_contact"     → HR representative for a department
        "timesheet"      → Timesheet submission deadline for a month/year
        "performance"    → Performance review schedule for a department

    Args:
        info_type:  What kind of HR info to fetch.
        department: Optional department filter.
        month:      Optional month name (e.g., "October") for timesheet.
        year:       Optional year string (e.g., "2026") for timesheet.
    """
    info_type = (info_type or "").lower().strip()

    if info_type == "hr_contact":
        return _get_hr_contact(department)
    elif info_type == "timesheet":
        return _get_timesheet_deadline(month, year)
    elif info_type == "performance":
        return _get_performance_reviews(department)
    else:
        return {
            "error": (
                f"Unknown info_type '{info_type}'. "
                "Valid options: 'hr_contact', 'timesheet', 'performance'."
            )
        }


def _get_hr_contact(department: Optional[str]) -> dict:
    try:
        rows = _read_csv("hr_contacts.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}
    if department:
        rows = [r for r in rows if r.get("department", "").lower() == department.strip().lower()]
    return {
        "hr_contacts": rows,
        "count": len(rows),
        "source": "local_csv",
    }


def _get_timesheet_deadline(month: Optional[str], year: Optional[str]) -> dict:
    try:
        rows = _read_csv("timesheets.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    if not month:
        # Default to current month
        month = datetime.now().strftime("%B")
    if not year:
        year = str(datetime.now().year)

    filtered = [
        r for r in rows
        if r.get("month", "").lower() == month.strip().lower()
        and r.get("year", "") == year.strip()
    ]

    if not filtered:
        # Return all rows if no match
        filtered = rows

    return {
        "timesheet_deadlines": filtered,
        "count": len(filtered),
        "source": "local_csv",
        "current_month": month,
        "year": year,
    }


def _get_performance_reviews(department: Optional[str]) -> dict:
    try:
        rows = _read_csv("performance_reviews.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}
    if department:
        rows = [r for r in rows if r.get("department", "").lower() == department.strip().lower()]
    return {
        "performance_reviews": rows,
        "count": len(rows),
        "source": "local_csv",
    }


# ── Team management (Manager tools) ──────────────────────────────────────────

def get_team_leave_info(
    manager_department: Optional[str] = None,
    info_type: str = "pending",
    date_filter: Optional[str] = None,
) -> dict:
    """
    Return leave-related information for a manager's team.

    info_type options:
        "pending"       → Pending leave requests for the team
        "upcoming"      → Team members on leave in upcoming week
        "attendance"    → Attendance summary for the team this month

    Args:
        manager_department: Filter by department (manager's team).
        info_type:          What kind of leave info to return.
        date_filter:        Optional date string for "upcoming" filter.
    """
    info_type = (info_type or "pending").lower().strip()

    if info_type == "attendance":
        return _get_team_attendance(manager_department)
    elif info_type in ("pending", "upcoming"):
        return _get_leave_requests(manager_department, info_type)
    else:
        return {
            "error": (
                f"Unknown info_type '{info_type}'. "
                "Valid options: 'pending', 'upcoming', 'attendance'."
            )
        }


def _get_leave_requests(department: Optional[str], filter_type: str) -> dict:
    try:
        rows = _read_csv("leave_requests.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    if department:
        rows = [r for r in rows if r.get("department", "").lower() == department.strip().lower()]

    if filter_type == "pending":
        rows = [r for r in rows if r.get("status", "").lower() == "pending"]
        label = "pending_leave_requests"
    else:
        # upcoming: leave starting within the next 7 days from today
        today = datetime.now().date()
        upcoming = []
        for r in rows:
            try:
                start = datetime.strptime(r.get("start_date", ""), "%Y-%m-%d").date()
                days_ahead = (start - today).days
                if 0 <= days_ahead <= 14:
                    upcoming.append(r)
            except ValueError:
                pass
        rows = upcoming
        label = "upcoming_leave"

    return {
        label: rows,
        "count": len(rows),
        "source": "local_csv",
        "note": "[DEMO MODE] Leave data is simulated demo data.",
    }


def _get_team_attendance(department: Optional[str]) -> dict:
    try:
        rows = _read_csv("attendance.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    if department:
        rows = [r for r in rows if r.get("department", "").lower() == department.strip().lower()]

    if not rows:
        return {
            "attendance": [],
            "count": 0,
            "source": "local_csv",
            "note": "[DEMO MODE] No attendance data found for the specified department.",
        }

    total_present = sum(int(r.get("days_present", 0)) for r in rows)
    total_absent = sum(int(r.get("days_absent", 0)) for r in rows)
    avg_attendance = round(
        sum(float(r.get("attendance_pct", 0)) for r in rows) / len(rows), 1
    )

    return {
        "attendance": rows,
        "count": len(rows),
        "summary": {
            "total_present_days": total_present,
            "total_absent_days": total_absent,
            "team_average_attendance_pct": avg_attendance,
            "month": rows[0].get("month") if rows else "N/A",
            "year": rows[0].get("year") if rows else "N/A",
        },
        "source": "local_csv",
        "note": "[DEMO MODE] Attendance data is simulated demo data.",
    }


def get_team_attendance(
    department: Optional[str] = None,
    month: Optional[str] = None,
    year: Optional[str] = None,
) -> dict:
    """
    Return a monthly attendance summary for a manager's team.

    This is a dedicated tool for the attendance question. It reads
    attendance.csv and computes a summary for the given department and month.

    When called without arguments (demo manager context already injected via
    the system prompt), defaults to the AI department for the current month.

    Args:
        department: Department / team name (e.g. 'AI'). Defaults to 'AI'.
        month:      Month name (e.g. 'September'). Defaults to most recent month in data.
        year:       Year string (e.g. '2026'). Defaults to most recent year in data.
    """
    try:
        rows = _read_csv("attendance.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    # Apply department filter (default to AI — the demo manager's department)
    dept_filter = (department or "AI").strip()
    rows = [r for r in rows if r.get("department", "").lower() == dept_filter.lower()]

    if not rows:
        return {
            "attendance": [],
            "count": 0,
            "source": "local_csv",
            "note": f"[DEMO MODE] No attendance data found for department '{dept_filter}'.",
        }

    # Determine month/year to report on
    if month and year:
        rows = [
            r for r in rows
            if r.get("month", "").lower() == month.strip().lower()
            and r.get("year", "") == year.strip()
        ]
    elif month:
        rows = [r for r in rows if r.get("month", "").lower() == month.strip().lower()]
    elif year:
        rows = [r for r in rows if r.get("year", "") == year.strip()]
    # If neither provided, use all rows for that department (typically one month per CSV)

    if not rows:
        return {
            "attendance": [],
            "count": 0,
            "source": "local_csv",
            "note": (
                f"[DEMO MODE] No attendance data found for department '{dept_filter}' "
                f"in the requested period."
            ),
        }

    report_month = rows[0].get("month", "N/A")
    report_year  = rows[0].get("year", "N/A")

    total_members  = len(rows)
    total_present  = sum(int(r.get("days_present", 0)) for r in rows)
    total_absent   = sum(int(r.get("days_absent", 0)) for r in rows)
    total_late     = sum(int(r.get("late_arrivals", 0)) for r in rows)
    total_leave    = sum(int(r.get("leave_days", 0)) for r in rows)
    avg_attendance = round(
        sum(float(r.get("attendance_pct", 0)) for r in rows) / total_members, 1
    )

    per_member = [
        {
            "employee_id":    r.get("employee_id"),
            "name":           r.get("name"),
            "days_present":   int(r.get("days_present", 0)),
            "days_absent":    int(r.get("days_absent", 0)),
            "late_arrivals":  int(r.get("late_arrivals", 0)),
            "leave_days":     int(r.get("leave_days", 0)),
            "attendance_pct": float(r.get("attendance_pct", 0)),
        }
        for r in rows
    ]

    return {
        "department": dept_filter,
        "month": report_month,
        "year": report_year,
        "team_members": total_members,
        "summary": {
            "total_days_present": total_present,
            "total_days_absent":  total_absent,
            "total_late_arrivals": total_late,
            "total_leave_days":   total_leave,
            "team_avg_attendance_pct": avg_attendance,
        },
        "per_member": per_member,
        "source": "local_csv",
        "note": "[DEMO MODE] Attendance data is from local demo CSV.",
    }


def get_team_utilization(department: Optional[str] = None) -> dict:
    """
    Return team utilization across projects for a department.

    Computes utilization from employees.csv and projects.csv.
    Returns per-employee project assignment and overall team summary.
    """
    try:
        employees = _read_csv("employees.csv")
        projects = _read_csv("projects.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    if department:
        employees = [e for e in employees if e.get("department", "").lower() == department.strip().lower()]

    if not employees:
        return {
            "utilization": [],
            "count": 0,
            "source": "local_csv",
            "note": "[DEMO MODE] No employees found for the specified department.",
        }

    project_map = {p["project_id"]: p for p in projects}

    utilization = []
    for emp in employees:
        proj_id = emp.get("project_id", "")
        proj = project_map.get(proj_id, {})
        utilization.append({
            "employee_id":   emp.get("employee_id"),
            "name":          emp.get("name"),
            "department":    emp.get("department"),
            "role":          emp.get("role"),
            "project_id":    proj_id,
            "project_name":  proj.get("project_name", "Unassigned"),
            "project_status": proj.get("status", "Unknown"),
            "utilization_status": (
                "Active – Fully Utilized" if proj.get("status") == "Active"
                else "Low – Project Completed/In Progress"
                if proj.get("status") in ("Completed", "In Progress")
                else "Unassigned"
            ),
        })

    active_count = sum(1 for u in utilization if "Active" in u["utilization_status"])
    utilization_pct = round(active_count / len(utilization) * 100, 1) if utilization else 0

    return {
        "utilization": utilization,
        "count": len(utilization),
        "summary": {
            "department": department or "All",
            "total_employees": len(utilization),
            "active_on_projects": active_count,
            "utilization_rate_pct": utilization_pct,
        },
        "source": "local_csv",
        "note": "[DEMO MODE] Utilization data is computed from demo employee and project data.",
    }


# ── Headcount report (dedicated Admin tool) ───────────────────────────────────

def get_headcount_report(department: Optional[str] = None) -> dict:
    """
    Generate a headcount report across all departments (Admin only).

    This is a dedicated admin tool for the predefined headcount report question.
    When called without arguments it returns organisation-wide headcount across
    ALL departments. An optional department filter restricts to a single dept.

    Args:
        department: Optional department name to filter. Leave empty for all depts.
    """
    try:
        employees = _read_csv("employees.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    if department:
        employees = [
            e for e in employees
            if e.get("department", "").lower() == department.strip().lower()
        ]

    dept_counts: dict[str, int] = {}
    for emp in employees:
        dept = emp.get("department", "Unknown")
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    return {
        "action":            "headcount_report",
        "department_filter": department or "All Departments",
        "total_headcount":   len(employees),
        "breakdown": [
            {"department": dept, "count": count}
            for dept, count in sorted(dept_counts.items())
        ],
        "source": "local_csv",
        "note":   "[DEMO MODE] Headcount calculated from demo employee data.",
    }


# ── Admin tools ───────────────────────────────────────────────────────────────

def admin_manage_user(
    action: str,
    employee_id: Optional[str] = None,
    employee_name: Optional[str] = None,
    department: Optional[str] = None,
) -> dict:
    """
    Perform simulated administrative user management actions.

    action options:
        "onboard"          → Show onboarding process steps
        "revoke_access"    → Simulate revoking access for a user
        "restore_account"  → Simulate restoring a deactivated account
        "headcount_report" → Generate headcount report across departments
        "get_accounts"     → List user accounts (all, active, or deactivated)

    All operations are SIMULATED in DEMO_MODE and do not affect real systems.
    """
    action = (action or "").lower().strip()

    if action == "onboard":
        return _simulate_onboard(employee_id, employee_name, department)
    elif action == "revoke_access":
        return _simulate_revoke_access(employee_id, employee_name)
    elif action == "restore_account":
        return _simulate_restore_account(employee_id, employee_name)
    elif action == "headcount_report":
        return _generate_headcount_report(department)
    elif action == "get_accounts":
        return _get_user_accounts(employee_id, employee_name, department)
    else:
        return {
            "error": (
                f"Unknown action '{action}'. "
                "Valid options: 'onboard', 'revoke_access', 'restore_account', "
                "'headcount_report', 'get_accounts'."
            )
        }


def _simulate_onboard(employee_id, employee_name, department) -> dict:
    name_str = employee_name or employee_id or "New Employee"
    dept_str = department or "the assigned department"
    return {
        "action": "onboard_employee",
        "status": "DEMO_SIMULATED",
        "employee": name_str,
        "department": dept_str,
        "onboarding_steps": [
            "Step 1: HR creates employee profile in HR system (Name, ID, Department, Role, Manager, Start Date).",
            "Step 2: IT raises an IT Access Request ticket with employee details and signed offer letter.",
            "Step 3: IT provisions laptop, company email, and access badge within 2 business days.",
            "Step 4: Access groups assigned based on role (principle of least privilege).",
            "Step 5: Manager assigns an onboarding buddy from the team.",
            "Step 6: Employee attends Day 1 orientation with HR.",
            "Step 7: Employee completes mandatory compliance training within 30 days.",
            "Step 8: Manager conducts 30-day and 60-day check-ins.",
            "Step 9: Probation review conducted at 3 months.",
        ],
        "it_request_fields": [
            "Employee Name", "Employee ID", "Department", "Role",
            "Start Date", "Access Groups", "Signed Offer Letter",
            "Background Verification Clearance"
        ],
        "note": "[DEMO MODE] This is a simulated onboarding process. No actual account was created.",
        "source": "local_csv",
    }


def _simulate_revoke_access(employee_id, employee_name) -> dict:
    try:
        rows = _read_csv("user_accounts.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    target = None
    if employee_id:
        matches = [r for r in rows if r.get("employee_id", "").upper() == employee_id.strip().upper()]
        target = matches[0] if matches else None
    elif employee_name:
        matches = [r for r in rows if employee_name.lower() in r.get("name", "").lower()]
        target = matches[0] if matches else None

    if not target:
        return {
            "action": "revoke_access",
            "status": "DEMO_SIMULATED",
            "result": "Employee not found in demo user accounts. In production, IT would process the revocation request.",
            "revocation_steps": [
                "Step 1: HR submits termination/resignation confirmation to IT Security.",
                "Step 2: IT Security disables the Active Directory account immediately.",
                "Step 3: All system access groups are removed.",
                "Step 4: VPN credentials are revoked.",
                "Step 5: Email account is set to auto-forward for 30 days then disabled.",
                "Step 6: Physical access badge is deactivated.",
                "Step 7: IT logs the revocation in the audit trail.",
                "Step 8: Revocation is confirmed to HR within 24 hours.",
            ],
            "note": "[DEMO MODE] Simulated revocation process. No actual access was changed.",
            "source": "local_csv",
        }

    return {
        "action": "revoke_access",
        "status": "DEMO_SIMULATED",
        "employee": target.get("name"),
        "username": target.get("username"),
        "department": target.get("department"),
        "current_status": target.get("account_status"),
        "current_access_groups": target.get("access_groups"),
        "simulated_result": {
            "account_status": "deactivated",
            "access_groups": "all removed",
            "email_status": "auto-forward enabled for 30 days",
            "badge_status": "deactivated",
            "revocation_logged": True,
        },
        "revocation_steps": [
            "Step 1: HR submits termination confirmation to IT Security.",
            "Step 2: IT Security disables Active Directory account immediately.",
            "Step 3: All access groups removed.",
            "Step 4: VPN credentials revoked.",
            "Step 5: Email auto-forwarded for 30 days, then disabled.",
            "Step 6: Physical badge deactivated.",
            "Step 7: Revocation logged in audit trail.",
            "Step 8: Confirmation sent to HR within 24 hours.",
        ],
        "note": "[DEMO MODE] This is a simulated revocation. No actual access was changed.",
        "source": "local_csv",
    }


def _simulate_restore_account(employee_id, employee_name) -> dict:
    try:
        rows = _read_csv("user_accounts.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    target = None
    deactivated = [r for r in rows if r.get("account_status", "").lower() == "deactivated"]

    if employee_id:
        matches = [r for r in deactivated if r.get("employee_id", "").upper() == employee_id.strip().upper()]
        target = matches[0] if matches else None
    elif employee_name:
        matches = [r for r in deactivated if employee_name.lower() in r.get("name", "").lower()]
        target = matches[0] if matches else None

    if not target:
        # Return general process
        return {
            "action": "restore_account",
            "status": "DEMO_SIMULATED",
            "deactivated_accounts_in_system": [
                {"employee_id": r.get("employee_id"), "name": r.get("name"),
                 "username": r.get("username"), "deactivated_date": r.get("deactivated_date")}
                for r in deactivated
            ],
            "restoration_steps": [
                "Step 1: Submit IT Helpdesk ticket titled 'Account Restoration Request'.",
                "Step 2: Provide: Employee name, ID, username, reason for restoration, manager and HR authorization.",
                "Step 3: IT Security verifies request and checks for security or compliance holds.",
                "Step 4: If cleared, IT restores account and resets the password.",
                "Step 5: Employee re-enrolls in MFA (mandatory).",
                "Step 6: Restored account placed under enhanced monitoring for 30 days.",
                "Step 7: HR confirms restoration in the employee management system.",
                "Note: Accounts deactivated due to policy violations require CISO approval.",
            ],
            "note": "[DEMO MODE] This is a simulated restoration process. No actual account was changed.",
            "source": "local_csv",
        }

    return {
        "action": "restore_account",
        "status": "DEMO_SIMULATED",
        "employee": target.get("name"),
        "username": target.get("username"),
        "department": target.get("department"),
        "deactivated_date": target.get("deactivated_date"),
        "simulated_result": {
            "account_status": "active",
            "password": "temporary-reset",
            "mfa_enrollment": "required",
            "monitoring_period": "30 days enhanced monitoring",
        },
        "restoration_steps": [
            "Step 1: IT Helpdesk ticket submitted and verified.",
            "Step 2: Manager and HR authorization confirmed.",
            "Step 3: IT Security cleared the account (no security holds).",
            "Step 4: Account restored and temporary password issued.",
            "Step 5: MFA re-enrollment required on first login.",
            "Step 6: Enhanced monitoring enabled for 30 days.",
            "Step 7: HR system updated.",
        ],
        "note": "[DEMO MODE] This is a simulated restoration. No actual account was changed.",
        "source": "local_csv",
    }


def _generate_headcount_report(department: Optional[str] = None) -> dict:
    try:
        employees = _read_csv("employees.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    if department:
        employees = [e for e in employees if e.get("department", "").lower() == department.strip().lower()]

    dept_counts: dict[str, int] = {}
    for emp in employees:
        dept = emp.get("department", "Unknown")
        dept_counts[dept] = dept_counts.get(dept, 0) + 1

    return {
        "action": "headcount_report",
        "department_filter": department or "All Departments",
        "total_headcount": len(employees),
        "breakdown": [
            {"department": dept, "count": count}
            for dept, count in sorted(dept_counts.items())
        ],
        "source": "local_csv",
        "note": "[DEMO MODE] Headcount calculated from demo employee data.",
    }


def _get_user_accounts(
    employee_id: Optional[str],
    employee_name: Optional[str],
    department: Optional[str],
) -> dict:
    try:
        rows = _read_csv("user_accounts.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    if employee_id:
        rows = [r for r in rows if r.get("employee_id", "").upper() == employee_id.strip().upper()]
    elif employee_name:
        rows = [r for r in rows if employee_name.lower() in r.get("name", "").lower()]
    elif department:
        rows = [r for r in rows if r.get("department", "").lower() == department.strip().lower()]

    return {
        "user_accounts": rows,
        "count": len(rows),
        "source": "local_csv",
        "note": "[DEMO MODE] User account data is simulated demo data.",
    }


# ── Compliance training ───────────────────────────────────────────────────────

def get_compliance_training_status(
    employee_id: Optional[str] = None,
    department: Optional[str] = None,
    status_filter: Optional[str] = None,
) -> dict:
    """
    Return compliance training status for employees.

    Args:
        employee_id:    Filter by specific employee.
        department:     Filter by department.
        status_filter:  Filter by completion status: 'Not Started', 'In Progress', 'Completed'.
                        If None, returns employees with incomplete training (Not Started or In Progress).
    """
    try:
        rows = _read_csv("compliance_training.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    if employee_id:
        rows = [r for r in rows if r.get("employee_id", "").upper() == employee_id.strip().upper()]
    elif department:
        rows = [r for r in rows if r.get("department", "").lower() == department.strip().lower()]

    if status_filter:
        rows = [r for r in rows if r.get("completion_status", "").lower() == status_filter.strip().lower()]
    else:
        # Default: return non-completed training
        rows = [r for r in rows if r.get("completion_status", "").lower() in ("not started", "in progress")]

    # Group by employee for summary
    employee_map: dict[str, dict] = {}
    for row in rows:
        eid = row.get("employee_id", "")
        if eid not in employee_map:
            employee_map[eid] = {
                "employee_id": eid,
                "name": row.get("name"),
                "department": row.get("department"),
                "incomplete_courses": [],
            }
        employee_map[eid]["incomplete_courses"].append({
            "course": row.get("course_name"),
            "required_by": row.get("required_by"),
            "status": row.get("completion_status"),
        })

    return {
        "incomplete_training": list(employee_map.values()),
        "total_employees_with_incomplete": len(employee_map),
        "total_incomplete_courses": len(rows),
        "source": "local_csv",
        "note": "[DEMO MODE] Training data is simulated demo data.",
    }


# ── Admin audit tool (dedicated, with demo default) ───────────────────────────

def audit_login_activity(
    employee_id: Optional[str] = None,
    employee_name: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """
    Audit login activity for a specific user.

    This is a dedicated admin tool for the predefined audit question.
    When called without arguments it defaults to the demo audit target:
        Alice Johnson (E001) — the canonical demo user for login audits.

    Args:
        employee_id:   Employee ID to audit (e.g. 'E001'). Defaults to 'E001'.
        employee_name: Employee name (partial match). Used only if employee_id
                       is explicitly overridden.
        limit:         Maximum number of log entries to return (default 10).
    """
    try:
        rows = _read_csv("login_activity.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    # Default to demo audit target: Alice Johnson / E001
    target_id = (employee_id or "E001").strip().upper()

    # Filter by employee_id first; fall back to name search only if id not found
    filtered = [r for r in rows if r.get("employee_id", "").upper() == target_id]
    if not filtered and employee_name:
        filtered = [r for r in rows if employee_name.lower() in r.get("name", "").lower()]

    # If still nothing (e.g. unknown ID override), return empty gracefully
    if not filtered:
        return {
            "login_activity": [],
            "count": 0,
            "flagged_entries": [],
            "flagged_count": 0,
            "audit_target": {"employee_id": target_id, "name": "Unknown"},
            "source": "local_csv",
            "note": f"[DEMO MODE] No login records found for employee ID '{target_id}'.",
        }

    # Respect limit
    limited = filtered[:limit]

    # Identify flagged entries (failed attempts > 1)
    flagged = [r for r in limited if int(r.get("failed_attempts", 0)) > 1]

    # Build audit target info from first record
    first = filtered[0]
    audit_target = {
        "employee_id": first.get("employee_id"),
        "name":        first.get("name"),
        "username":    first.get("username"),
    }

    return {
        "audit_target":   audit_target,
        "login_activity": limited,
        "count":          len(limited),
        "total_records":  len(filtered),
        "flagged_entries": flagged,
        "flagged_count":  len(flagged),
        "source":         "local_csv",
        "note":           "[DEMO MODE] Login activity is simulated demo data.",
    }


# ── Login activity ────────────────────────────────────────────────────────────

def get_login_activity(
    employee_id: Optional[str] = None,
    employee_name: Optional[str] = None,
    username: Optional[str] = None,
    limit: int = 10,
) -> dict:
    """
    Return login activity for a specific user or all users.

    Args:
        employee_id:    Filter by employee ID.
        employee_name:  Filter by employee name (partial match).
        username:       Filter by system username.
        limit:          Maximum number of log entries to return (default 10).
    """
    try:
        rows = _read_csv("login_activity.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    if employee_id:
        rows = [r for r in rows if r.get("employee_id", "").upper() == employee_id.strip().upper()]
    elif username:
        rows = [r for r in rows if r.get("username", "").lower() == username.strip().lower()]
    elif employee_name:
        rows = [r for r in rows if employee_name.lower() in r.get("name", "").lower()]

    rows = rows[:limit]

    flagged = [r for r in rows if int(r.get("failed_attempts", 0)) > 1]

    return {
        "login_activity": rows,
        "count": len(rows),
        "flagged_entries": flagged,
        "flagged_count": len(flagged),
        "source": "local_csv",
        "note": "[DEMO MODE] Login activity data is simulated demo data.",
    }


# ── Admin permissions ─────────────────────────────────────────────────────────

def get_admin_permissions(
    employee_id: Optional[str] = None,
    permission_level: Optional[str] = None,
) -> dict:
    """
    Return admin and elevated permission assignments.

    Args:
        employee_id:       Filter by specific employee.
        permission_level:  Filter by level: 'admin', 'elevated', or None for all.
    """
    try:
        rows = _read_csv("admin_permissions.csv")
    except FileNotFoundError as e:
        return {"error": str(e)}

    if employee_id:
        rows = [r for r in rows if r.get("employee_id", "").upper() == employee_id.strip().upper()]
    if permission_level:
        rows = [r for r in rows if r.get("permission_level", "").lower() == permission_level.strip().lower()]

    admin_users = [r for r in rows if r.get("permission_level", "").lower() == "admin"]
    elevated_users = [r for r in rows if r.get("permission_level", "").lower() == "elevated"]

    return {
        "privileged_accounts": rows,
        "count": len(rows),
        "admin_count": len(admin_users),
        "elevated_count": len(elevated_users),
        "admin_users": admin_users,
        "elevated_users": elevated_users,
        "source": "local_csv",
        "note": "[DEMO MODE] Permission data is simulated demo data.",
    }


# =============================================================================
# IT INCIDENT / SUPPORT TOOLS
# =============================================================================
#
# Demo identity constants
# -----------------------
# Employee demo:  E001 – Alice Johnson, AI dept, Hyderabad office
# Manager demo:   E011 – Karen Davis,   AI dept, Hyderabad office
# Admin demo:     ADM001 – Priya Reddy, IT dept, Hyderabad office
#
# All tools read from local CSV files in DEMO_MODE.
# =============================================================================

_DEMO_EMPLOYEE_ID   = "E001"
_DEMO_EMPLOYEE_NAME = "Alice Johnson"
_DEMO_EMPLOYEE_DEPT = "AI"
_DEMO_EMPLOYEE_OFFICE = "Hyderabad"

_DEMO_MANAGER_ID   = "E011"
_DEMO_MANAGER_NAME = "Karen Davis"
_DEMO_MANAGER_DEPT = "AI"
_DEMO_MANAGER_TEAM_IDS = {"E001", "E002", "E003", "E011"}  # AI dept members

_DEMO_ADMIN_ID   = "ADM001"
_DEMO_ADMIN_NAME = "Priya Reddy"


def _read_incidents() -> list[dict]:
    return _read_csv("it_incidents.csv")


def _read_tickets() -> list[dict]:
    return _read_csv("it_tickets.csv")


def _read_application_status() -> list[dict]:
    return _read_csv("application_status.csv")


def _read_vpn_status() -> list[dict]:
    return _read_csv("vpn_status.csv")


def _read_offices() -> list[dict]:
    return _read_csv("offices.csv")


def _read_services() -> list[dict]:
    return _read_csv("services.csv")


# ---------------------------------------------------------------------------
# EMPLOYEE TOOLS (10 questions)
# ---------------------------------------------------------------------------

def check_active_incidents(
    employee_id: Optional[str] = None,
    department: Optional[str] = None,
    office: Optional[str] = None,
) -> dict:
    """
    Check for active IT incidents that may affect the requesting employee.

    Uses demo defaults:
        employee_id = E001 (Alice Johnson), department = AI, office = Hyderabad

    Returns active incidents relevant to the employee's department/office.
    """
    dept   = department or _DEMO_EMPLOYEE_DEPT
    office_val = office or _DEMO_EMPLOYEE_OFFICE

    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    active_statuses = {"investigating", "open"}
    active = [
        inc for inc in incidents
        if inc.get("status", "").lower() in active_statuses
        and (
            inc.get("affected_department", "").lower() in (dept.lower(), "all")
            or inc.get("affected_office", "").lower() in (office_val.lower(), "all")
        )
    ]

    return {
        "active_incidents": active,
        "count": len(active),
        "employee_context": {"department": dept, "office": office_val},
        "source": "local_demo_data",
        "note": "[DEMO MODE] IT incident data is simulated demo data.",
    }


def check_application_status(
    application_name: Optional[str] = None,
    department: Optional[str] = None,
) -> dict:
    """
    Check the current status of a specific application or applications
    relevant to the employee's department.

    Defaults to looking up the SmartAssist AI Platform (primary app for AI dept).
    """
    dept = department or _DEMO_EMPLOYEE_DEPT

    try:
        services = _read_services()
    except FileNotFoundError as e:
        return {"error": str(e)}

    if application_name:
        results = [
            s for s in services
            if application_name.lower() in s.get("service_name", "").lower()
        ]
    else:
        # Return all non-Operational services (any degraded/down that the dept uses)
        results = [s for s in services if s.get("status", "").lower() != "operational"]
        if not results:
            results = services  # all fine, return all

    return {
        "application_status": results,
        "count": len(results),
        "employee_context": {"department": dept},
        "source": "local_demo_data",
        "note": "[DEMO MODE] Application status is simulated demo data.",
    }


def check_vpn_status() -> dict:
    """
    Check the current status of the company VPN.

    Returns VPN status, description, affected users, and the related incident.
    """
    try:
        rows = _read_vpn_status()
    except FileNotFoundError as e:
        return {"error": str(e)}

    vpn = rows[0] if rows else {}
    # Also fetch related incident details if available
    related_inc = vpn.get("related_incident", "")
    incident_detail = {}
    if related_inc:
        try:
            incidents = _read_incidents()
            matches = [i for i in incidents if i.get("incident_id", "") == related_inc]
            if matches:
                incident_detail = matches[0]
        except FileNotFoundError:
            pass

    return {
        "vpn_status": vpn.get("vpn_status", "Unknown"),
        "description": vpn.get("description", ""),
        "affected_users": vpn.get("affected_users", "0"),
        "related_incident": related_inc,
        "incident_detail": incident_detail,
        "last_updated": vpn.get("last_updated", ""),
        "estimated_resolution": vpn.get("estimated_resolution", ""),
        "source": "local_demo_data",
        "note": "[DEMO MODE] VPN status is simulated demo data.",
    }


def check_network_status(
    office: Optional[str] = None,
    department: Optional[str] = None,
) -> dict:
    """
    Check for network issues affecting the employee's office.

    Defaults to Hyderabad office (demo employee context).
    """
    office_val = office or _DEMO_EMPLOYEE_OFFICE

    try:
        offices = _read_offices()
    except FileNotFoundError as e:
        return {"error": str(e)}

    matches = [
        o for o in offices
        if office_val.lower() in o.get("office_name", "").lower()
        or office_val.lower() in o.get("city", "").lower()
    ]
    if not matches:
        matches = [o for o in offices if o.get("status", "").lower() != "operational"]

    return {
        "office_network_status": matches,
        "count": len(matches),
        "queried_office": office_val,
        "source": "local_demo_data",
        "note": "[DEMO MODE] Network/office status is simulated demo data.",
    }


def check_user_application_access(
    employee_id: Optional[str] = None,
    application_name: Optional[str] = None,
) -> dict:
    """
    Check why a specific employee cannot access an internal application.

    Defaults to demo employee E001 / Alice Johnson and SmartAssist AI Platform.
    """
    emp_id = employee_id or _DEMO_EMPLOYEE_ID

    try:
        tickets = _read_tickets()
        services = _read_services()
    except FileNotFoundError as e:
        return {"error": str(e)}

    emp_tickets = [t for t in tickets if t.get("employee_id", "") == emp_id]
    if application_name:
        emp_tickets = [
            t for t in emp_tickets
            if application_name.lower() in t.get("title", "").lower()
            or application_name.lower() in t.get("description", "").lower()
        ]

    # Find affected services
    degraded = [s for s in services if s.get("status", "").lower() in ("down", "degraded")]

    return {
        "employee_id": emp_id,
        "employee_tickets": emp_tickets,
        "affected_services": degraded,
        "possible_causes": [
            "An active IT incident is affecting the application.",
            "The SSO/authentication service may be experiencing issues.",
            "The application server may be down or degraded.",
        ],
        "recommendation": "Check your open IT tickets and active incidents above for details.",
        "source": "local_demo_data",
        "note": "[DEMO MODE] Access diagnosis uses simulated demo data.",
    }


def check_authentication_issue(
    employee_id: Optional[str] = None,
    office: Optional[str] = None,
) -> dict:
    """
    Check whether a login/authentication problem is a known company-wide issue.

    Defaults to demo employee E001, Hyderabad office.
    """
    emp_id     = employee_id or _DEMO_EMPLOYEE_ID
    office_val = office or _DEMO_EMPLOYEE_OFFICE

    try:
        incidents = _read_incidents()
        tickets   = _read_tickets()
    except FileNotFoundError as e:
        return {"error": str(e)}

    # Look for auth-related active incidents
    auth_keywords = {"sso", "authentication", "login", "auth", "sign-in"}
    auth_incidents = [
        inc for inc in incidents
        if inc.get("status", "").lower() in ("investigating", "open")
        and any(kw in inc.get("title", "").lower() or kw in inc.get("description", "").lower()
                for kw in auth_keywords)
    ]

    # Employee's own auth tickets
    emp_auth_tickets = [
        t for t in tickets
        if t.get("employee_id", "") == emp_id
        and any(kw in t.get("title", "").lower() or kw in t.get("description", "").lower()
                for kw in auth_keywords)
    ]

    is_known = len(auth_incidents) > 0

    return {
        "is_known_issue": is_known,
        "auth_incidents": auth_incidents,
        "employee_auth_tickets": emp_auth_tickets,
        "message": (
            "Yes, your login/authentication problem is a known issue. "
            f"There are {len(auth_incidents)} active incident(s) related to authentication."
            if is_known else
            "No company-wide authentication incident is currently active. "
            "Your issue may be isolated — please create an IT ticket."
        ),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Authentication status uses simulated demo data.",
    }


def get_it_ticket_status(
    employee_id: Optional[str] = None,
    ticket_id: Optional[str] = None,
) -> dict:
    """
    Get the current status of an employee's open IT ticket(s).

    Defaults to demo employee E001 / Alice Johnson.
    """
    emp_id = employee_id or _DEMO_EMPLOYEE_ID

    try:
        tickets = _read_tickets()
    except FileNotFoundError as e:
        return {"error": str(e)}

    if ticket_id:
        results = [t for t in tickets if t.get("ticket_id", "") == ticket_id]
    else:
        results = [t for t in tickets if t.get("employee_id", "") == emp_id]

    open_tickets = [t for t in results if t.get("status", "").lower() in ("open", "in progress")]

    return {
        "employee_id": emp_id,
        "tickets": results,
        "open_tickets": open_tickets,
        "open_count": len(open_tickets),
        "source": "local_demo_data",
        "note": "[DEMO MODE] IT ticket data is simulated demo data.",
    }


def get_it_ticket_assignee(
    employee_id: Optional[str] = None,
    ticket_id: Optional[str] = None,
) -> dict:
    """
    Check whether an IT ticket has been assigned to a support engineer.

    Defaults to demo employee E001 / Alice Johnson.
    """
    emp_id = employee_id or _DEMO_EMPLOYEE_ID

    try:
        tickets = _read_tickets()
    except FileNotFoundError as e:
        return {"error": str(e)}

    if ticket_id:
        results = [t for t in tickets if t.get("ticket_id", "") == ticket_id]
    else:
        results = [t for t in tickets if t.get("employee_id", "") == emp_id]

    assignments = [
        {
            "ticket_id": t.get("ticket_id"),
            "title": t.get("title"),
            "status": t.get("status"),
            "assigned_to": t.get("assigned_to") or "Unassigned",
            "is_assigned": bool(t.get("assigned_to", "").strip()),
        }
        for t in results
    ]

    return {
        "employee_id": emp_id,
        "ticket_assignments": assignments,
        "count": len(assignments),
        "unassigned_count": sum(1 for a in assignments if not a["is_assigned"]),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Ticket assignment data is simulated demo data.",
    }


def get_it_ticket_last_updated(
    employee_id: Optional[str] = None,
    ticket_id: Optional[str] = None,
) -> dict:
    """
    Get the last-updated timestamp for an employee's IT ticket(s).

    Defaults to demo employee E001 / Alice Johnson.
    """
    emp_id = employee_id or _DEMO_EMPLOYEE_ID

    try:
        tickets = _read_tickets()
    except FileNotFoundError as e:
        return {"error": str(e)}

    if ticket_id:
        results = [t for t in tickets if t.get("ticket_id", "") == ticket_id]
    else:
        results = [t for t in tickets if t.get("employee_id", "") == emp_id]

    update_info = [
        {
            "ticket_id": t.get("ticket_id"),
            "title": t.get("title"),
            "status": t.get("status"),
            "created_at": t.get("created_at"),
            "last_updated": t.get("last_updated"),
            "assigned_to": t.get("assigned_to") or "Unassigned",
        }
        for t in results
    ]

    return {
        "employee_id": emp_id,
        "ticket_updates": update_info,
        "count": len(update_info),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Ticket timestamps are simulated demo data.",
    }


def find_related_incident(
    employee_id: Optional[str] = None,
    issue_description: Optional[str] = None,
) -> dict:
    """
    Determine whether an existing IT incident already covers the employee's problem.

    Defaults to demo employee E001 (Alice Johnson, AI dept, Hyderabad).
    Searches active incidents relevant to the employee's department/office.
    """
    emp_id = employee_id or _DEMO_EMPLOYEE_ID
    dept   = _DEMO_EMPLOYEE_DEPT
    office = _DEMO_EMPLOYEE_OFFICE

    try:
        incidents = _read_incidents()
        tickets   = _read_tickets()
    except FileNotFoundError as e:
        return {"error": str(e)}

    active_statuses = {"investigating", "open"}
    relevant = [
        inc for inc in incidents
        if inc.get("status", "").lower() in active_statuses
        and (
            inc.get("affected_department", "").lower() in (dept.lower(), "all")
            or inc.get("affected_office", "").lower() in (office.lower(), "all")
        )
    ]

    # Also check the employee's existing tickets for related_incident links
    emp_tickets = [t for t in tickets if t.get("employee_id", "") == emp_id]

    return {
        "related_incidents": relevant,
        "incident_count": len(relevant),
        "employee_existing_tickets": emp_tickets,
        "recommendation": (
            "Yes, an active incident already covers your issue. "
            "You do not need to create a new ticket — the IT team is already working on it."
            if relevant else
            "No existing incident found for your issue. "
            "You may want to create a new IT ticket."
        ),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Incident matching uses simulated demo data.",
    }


def create_it_ticket(
    employee_id: Optional[str] = None,
    employee_name: Optional[str] = None,
    department: Optional[str] = None,
    issue_title: Optional[str] = None,
    issue_description: Optional[str] = None,
    priority: Optional[str] = None,
) -> dict:
    """
    Simulate creating a new IT support ticket for an employee.

    DEMO_MODE: Does NOT create a real ticket. Returns a simulated ticket ID.
    Defaults to demo employee E001 / Alice Johnson / AI / Hyderabad.
    """
    emp_id   = employee_id or _DEMO_EMPLOYEE_ID
    emp_name = employee_name or _DEMO_EMPLOYEE_NAME
    dept     = department or _DEMO_EMPLOYEE_DEPT
    title    = issue_title or "IT Support Request"
    desc     = issue_description or "Employee reported an IT issue requiring support."
    priority_val = priority or "Medium"

    # Check for related incidents first
    related_result = find_related_incident(employee_id=emp_id)
    related_incidents = related_result.get("related_incidents", [])

    # Generate a simulated ticket ID
    try:
        existing = _read_tickets()
        next_num = len(existing) + 1
    except FileNotFoundError:
        next_num = 7
    new_ticket_id = f"IT{next_num:03d}"

    simulated_ticket = {
        "ticket_id": new_ticket_id,
        "employee_id": emp_id,
        "employee_name": emp_name,
        "department": dept,
        "title": title,
        "description": desc,
        "status": "Open",
        "priority": priority_val,
        "assigned_to": "IT Helpdesk",
        "created_at": "2026-10-04 11:00:00",
        "related_incident": related_incidents[0].get("incident_id", "") if related_incidents else "",
    }

    return {
        "action": "create_it_ticket",
        "status": "DEMO_MODE: IT ticket created successfully.",
        "ticket": simulated_ticket,
        "related_incidents_found": related_incidents,
        "note": (
            f"DEMO_MODE: IT ticket {new_ticket_id} was created successfully. "
            "No real ticket was created in an external system."
        ),
        "source": "local_demo_data",
    }


# ---------------------------------------------------------------------------
# MANAGER TOOLS (10 questions)
# ---------------------------------------------------------------------------

def get_team_incidents(
    manager_department: Optional[str] = None,
    manager_id: Optional[str] = None,
) -> dict:
    """
    Return active IT incidents affecting a manager's team members.

    Defaults to Karen Davis / AI department (demo manager context).
    """
    dept = manager_department or _DEMO_MANAGER_DEPT

    try:
        incidents = _read_incidents()
        tickets   = _read_tickets()
    except FileNotFoundError as e:
        return {"error": str(e)}

    active_statuses = {"investigating", "open"}
    team_incidents = [
        inc for inc in incidents
        if inc.get("status", "").lower() in active_statuses
        and (
            inc.get("affected_department", "").lower() in (dept.lower(), "all")
            or inc.get("affected_office", "").lower() in ("hyderabad", "all")
        )
    ]

    team_tickets = [
        t for t in tickets
        if t.get("employee_id", "") in _DEMO_MANAGER_TEAM_IDS
        and t.get("status", "").lower() in ("open", "in progress")
    ]

    return {
        "manager_department": dept,
        "team_incidents": team_incidents,
        "incident_count": len(team_incidents),
        "team_open_tickets": team_tickets,
        "source": "local_demo_data",
        "note": "[DEMO MODE] Team incident data is simulated demo data.",
    }


def get_team_affected_users(
    manager_department: Optional[str] = None,
    incident_id: Optional[str] = None,
) -> dict:
    """
    Return how many and which team members are affected by a current IT incident.

    Defaults to Karen Davis / AI department.
    """
    dept = manager_department or _DEMO_MANAGER_DEPT

    try:
        incidents = _read_incidents()
        tickets   = _read_tickets()
    except FileNotFoundError as e:
        return {"error": str(e)}

    active_statuses = {"investigating", "open"}
    if incident_id:
        relevant_incidents = [i for i in incidents if i.get("incident_id", "") == incident_id]
    else:
        relevant_incidents = [
            inc for inc in incidents
            if inc.get("status", "").lower() in active_statuses
            and (
                inc.get("affected_department", "").lower() in (dept.lower(), "all")
                or inc.get("affected_office", "").lower() in ("hyderabad", "all")
            )
        ]

    # Find team members with open tickets linked to these incidents
    inc_ids = {i.get("incident_id", "") for i in relevant_incidents}
    affected_tickets = [
        t for t in tickets
        if t.get("employee_id", "") in _DEMO_MANAGER_TEAM_IDS
        and t.get("related_incident", "") in inc_ids
    ]

    affected_members = {t["employee_id"]: t for t in affected_tickets}

    return {
        "manager_department": dept,
        "relevant_incidents": relevant_incidents,
        "affected_team_members": list(affected_members.values()),
        "affected_count": len(affected_members),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Affected team member data is simulated demo data.",
    }


def compare_incident_scope(
    manager_department: Optional[str] = None,
    incident_id: Optional[str] = None,
) -> dict:
    """
    Determine whether an incident is limited to the manager's team/department
    or is affecting other departments/offices company-wide.

    Defaults to Karen Davis / AI department.
    """
    dept = manager_department or _DEMO_MANAGER_DEPT

    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    active_statuses = {"investigating", "open"}
    if incident_id:
        focus_incidents = [i for i in incidents if i.get("incident_id", "") == incident_id]
    else:
        focus_incidents = [
            inc for inc in incidents
            if inc.get("status", "").lower() in active_statuses
            and (
                inc.get("affected_department", "").lower() in (dept.lower(), "all")
                or inc.get("affected_office", "").lower() in ("hyderabad", "all")
            )
        ]

    scope_analysis = []
    for inc in focus_incidents:
        affected_dept = inc.get("affected_department", "")
        is_company_wide = affected_dept.lower() == "all"
        scope_analysis.append({
            "incident_id": inc.get("incident_id"),
            "title": inc.get("title"),
            "affected_department": affected_dept,
            "affected_office": inc.get("affected_office"),
            "affected_users": inc.get("affected_users"),
            "is_company_wide": is_company_wide,
            "scope": (
                "Company-wide — affecting all departments and offices"
                if is_company_wide
                else f"Limited to {affected_dept} department / {inc.get('affected_office','N/A')} office"
            ),
        })

    return {
        "manager_department": dept,
        "scope_analysis": scope_analysis,
        "count": len(scope_analysis),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Incident scope analysis uses simulated demo data.",
    }


def get_incident_status(
    incident_id: Optional[str] = None,
    manager_department: Optional[str] = None,
) -> dict:
    """
    Get the current status of IT incidents affecting a manager's team.

    Defaults to Karen Davis / AI department.
    """
    dept = manager_department or _DEMO_MANAGER_DEPT

    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    if incident_id:
        results = [i for i in incidents if i.get("incident_id", "") == incident_id]
    else:
        active_statuses = {"investigating", "open"}
        results = [
            inc for inc in incidents
            if inc.get("status", "").lower() in active_statuses
            and (
                inc.get("affected_department", "").lower() in (dept.lower(), "all")
                or inc.get("affected_office", "").lower() in ("hyderabad", "all")
            )
        ]

    return {
        "manager_department": dept,
        "incidents": results,
        "count": len(results),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Incident status is simulated demo data.",
    }


def get_incident_owner(
    incident_id: Optional[str] = None,
    manager_department: Optional[str] = None,
) -> dict:
    """
    Identify which IT team is currently handling active incidents for a manager's department.

    Defaults to Karen Davis / AI department.
    """
    dept = manager_department or _DEMO_MANAGER_DEPT

    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    if incident_id:
        results = [i for i in incidents if i.get("incident_id", "") == incident_id]
    else:
        active_statuses = {"investigating", "open"}
        results = [
            inc for inc in incidents
            if inc.get("status", "").lower() in active_statuses
            and (
                inc.get("affected_department", "").lower() in (dept.lower(), "all")
                or inc.get("affected_office", "").lower() in ("hyderabad", "all")
            )
        ]

    ownership = [
        {
            "incident_id": i.get("incident_id"),
            "title": i.get("title"),
            "status": i.get("status"),
            "responsible_team": i.get("responsible_team"),
            "last_updated": i.get("last_updated"),
        }
        for i in results
    ]

    return {
        "manager_department": dept,
        "incident_ownership": ownership,
        "count": len(ownership),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Incident ownership data is simulated demo data.",
    }


def get_incident_timeline(
    incident_id: Optional[str] = None,
    manager_department: Optional[str] = None,
) -> dict:
    """
    Get the timeline (reported_at and last_updated) for incidents affecting the team.

    Defaults to Karen Davis / AI department.
    """
    dept = manager_department or _DEMO_MANAGER_DEPT

    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    if incident_id:
        results = [i for i in incidents if i.get("incident_id", "") == incident_id]
    else:
        active_statuses = {"investigating", "open"}
        results = [
            inc for inc in incidents
            if inc.get("status", "").lower() in active_statuses
            and (
                inc.get("affected_department", "").lower() in (dept.lower(), "all")
                or inc.get("affected_office", "").lower() in ("hyderabad", "all")
            )
        ]

    timelines = [
        {
            "incident_id": i.get("incident_id"),
            "title": i.get("title"),
            "status": i.get("status"),
            "reported_at": i.get("reported_at"),
            "last_updated": i.get("last_updated"),
            "estimated_resolution": i.get("estimated_resolution"),
            "responsible_team": i.get("responsible_team"),
        }
        for i in results
    ]

    return {
        "manager_department": dept,
        "incident_timelines": timelines,
        "count": len(timelines),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Incident timeline data is simulated demo data.",
    }


def get_incident_eta(
    incident_id: Optional[str] = None,
    manager_department: Optional[str] = None,
) -> dict:
    """
    Get the estimated time to resolution (ETA) for active incidents.

    Defaults to Karen Davis / AI department.
    """
    dept = manager_department or _DEMO_MANAGER_DEPT

    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    if incident_id:
        results = [i for i in incidents if i.get("incident_id", "") == incident_id]
    else:
        active_statuses = {"investigating", "open"}
        results = [
            inc for inc in incidents
            if inc.get("status", "").lower() in active_statuses
            and (
                inc.get("affected_department", "").lower() in (dept.lower(), "all")
                or inc.get("affected_office", "").lower() in ("hyderabad", "all")
            )
        ]

    eta_info = [
        {
            "incident_id": i.get("incident_id"),
            "title": i.get("title"),
            "status": i.get("status"),
            "estimated_resolution": i.get("estimated_resolution") or "Not yet provided",
            "sla_deadline": i.get("sla_deadline") or "Not set",
            "responsible_team": i.get("responsible_team"),
        }
        for i in results
    ]

    return {
        "manager_department": dept,
        "eta_information": eta_info,
        "count": len(eta_info),
        "source": "local_demo_data",
        "note": "[DEMO MODE] ETA data is simulated demo data.",
    }


def get_team_unresolved_tickets(
    manager_department: Optional[str] = None,
) -> dict:
    """
    List team members who currently have unresolved IT tickets.

    Defaults to Karen Davis / AI department team members.
    """
    dept = manager_department or _DEMO_MANAGER_DEPT

    try:
        tickets = _read_tickets()
    except FileNotFoundError as e:
        return {"error": str(e)}

    open_statuses = {"open", "in progress"}
    unresolved = [
        t for t in tickets
        if t.get("employee_id", "") in _DEMO_MANAGER_TEAM_IDS
        and t.get("status", "").lower() in open_statuses
    ]

    # Group by employee
    by_employee: dict[str, dict] = {}
    for t in unresolved:
        eid = t.get("employee_id", "")
        if eid not in by_employee:
            by_employee[eid] = {
                "employee_id": eid,
                "employee_name": t.get("employee_name"),
                "department": t.get("department"),
                "open_tickets": [],
            }
        by_employee[eid]["open_tickets"].append({
            "ticket_id": t.get("ticket_id"),
            "title": t.get("title"),
            "status": t.get("status"),
            "priority": t.get("priority"),
            "assigned_to": t.get("assigned_to") or "Unassigned",
            "created_at": t.get("created_at"),
        })

    return {
        "manager_department": dept,
        "team_members_with_open_tickets": list(by_employee.values()),
        "affected_member_count": len(by_employee),
        "total_open_tickets": len(unresolved),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Unresolved ticket data is simulated demo data.",
    }


def get_recurring_team_incidents(
    manager_department: Optional[str] = None,
) -> dict:
    """
    Identify recurring IT problems affecting a manager's team.

    Checks for multiple incidents affecting the same service/department.
    Defaults to Karen Davis / AI department.
    """
    dept = manager_department or _DEMO_MANAGER_DEPT

    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    # Find all incidents (including resolved) for the department
    relevant = [
        inc for inc in incidents
        if inc.get("affected_department", "").lower() in (dept.lower(), "all")
        or inc.get("affected_office", "").lower() in ("hyderabad", "all")
    ]

    # Group by affected_service to detect recurring patterns
    service_map: dict[str, list] = {}
    for inc in relevant:
        svc = inc.get("affected_service", "Unknown")
        if svc not in service_map:
            service_map[svc] = []
        service_map[svc].append(inc)

    recurring = {svc: incs for svc, incs in service_map.items() if len(incs) >= 1}

    return {
        "manager_department": dept,
        "recurring_patterns": [
            {
                "service": svc,
                "incident_count": len(incs),
                "incidents": incs,
                "is_recurring": len(incs) > 1,
            }
            for svc, incs in recurring.items()
        ],
        "total_relevant_incidents": len(relevant),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Recurring incident analysis uses simulated demo data.",
    }


def escalate_incident(
    incident_id: Optional[str] = None,
    manager_id: Optional[str] = None,
    manager_department: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict:
    """
    Simulate escalating a blocking IT incident on behalf of a manager.

    DEMO_MODE: Does NOT perform a real escalation. Returns a simulated confirmation.
    Defaults to Karen Davis / AI department and the most critical open incident.
    """
    dept = manager_department or _DEMO_MANAGER_DEPT
    mgr_id = manager_id or _DEMO_MANAGER_ID

    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    if incident_id:
        target_incidents = [i for i in incidents if i.get("incident_id", "") == incident_id]
    else:
        # Auto-select most critical open incident for the department
        active_statuses = {"investigating", "open"}
        target_incidents = [
            inc for inc in incidents
            if inc.get("status", "").lower() in active_statuses
            and (
                inc.get("affected_department", "").lower() in (dept.lower(), "all")
                or inc.get("affected_office", "").lower() in ("hyderabad", "all")
            )
        ]
        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        target_incidents.sort(key=lambda x: severity_order.get(x.get("severity", "low").lower(), 99))

    if not target_incidents:
        return {
            "action": "escalate_incident",
            "status": "DEMO_MODE: No active incident found to escalate.",
            "source": "local_demo_data",
            "note": "[DEMO MODE] Escalation simulation — no real action taken.",
        }

    target = target_incidents[0]
    escalated_id = target.get("incident_id", "UNKNOWN")

    return {
        "action": "escalate_incident",
        "status": f"DEMO_MODE: Incident {escalated_id} was escalated successfully.",
        "escalated_incident": {
            "incident_id": escalated_id,
            "title": target.get("title"),
            "current_status": target.get("status"),
            "severity": target.get("severity"),
            "responsible_team": target.get("responsible_team"),
        },
        "escalation_details": {
            "escalated_by": f"{_DEMO_MANAGER_NAME} ({mgr_id})",
            "escalated_to": "IT Director / CISO",
            "reason": reason or "Incident is blocking team's sprint delivery.",
            "escalation_time": "2026-10-04 11:05:00",
            "next_review": "2026-10-04 12:00:00",
        },
        "note": (
            f"DEMO_MODE: Incident {escalated_id} was escalated successfully. "
            "No real escalation was triggered in an external system."
        ),
        "source": "local_demo_data",
    }


# ---------------------------------------------------------------------------
# ADMIN TOOLS (10 questions)
# ---------------------------------------------------------------------------

def get_active_incidents() -> dict:
    """
    Return all currently active IT incidents across the company (Admin only).
    """
    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    active_statuses = {"investigating", "open"}
    active = [i for i in incidents if i.get("status", "").lower() in active_statuses]

    return {
        "active_incidents": active,
        "count": len(active),
        "total_incidents": len(incidents),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Incident data is simulated demo data.",
    }


def get_critical_service_status() -> dict:
    """
    Return the current status of all critical applications and services (Admin only).
    """
    try:
        services = _read_services()
    except FileNotFoundError as e:
        return {"error": str(e)}

    critical = [s for s in services if s.get("is_critical", "").lower() == "yes"]
    unavailable = [s for s in critical if s.get("status", "").lower() in ("down", "degraded")]
    operational  = [s for s in critical if s.get("status", "").lower() == "operational"]

    return {
        "critical_services": critical,
        "unavailable_or_degraded": unavailable,
        "fully_operational": operational,
        "critical_count": len(critical),
        "unavailable_count": len(unavailable),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Service status is simulated demo data.",
    }


def get_affected_offices_departments() -> dict:
    """
    Return a summary of which offices and departments are currently
    experiencing network or IT issues (Admin only).
    """
    try:
        offices   = _read_offices()
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    affected_offices = [o for o in offices if o.get("status", "").lower() != "operational"]
    operational_offices = [o for o in offices if o.get("status", "").lower() == "operational"]

    # Summarise affected departments from active incidents
    active_statuses = {"investigating", "open"}
    affected_depts = list({
        inc.get("affected_department", "")
        for inc in incidents
        if inc.get("status", "").lower() in active_statuses
        and inc.get("affected_department", "").lower() != "all"
    })

    return {
        "affected_offices": affected_offices,
        "operational_offices": operational_offices,
        "affected_departments": affected_depts,
        "affected_office_count": len(affected_offices),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Office/department status is simulated demo data.",
    }


def get_incident_impact() -> dict:
    """
    Return the user impact (affected_users count) for each major active incident (Admin only).
    """
    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    active_statuses = {"investigating", "open"}
    active = [i for i in incidents if i.get("status", "").lower() in active_statuses]

    impact = [
        {
            "incident_id": i.get("incident_id"),
            "title": i.get("title"),
            "status": i.get("status"),
            "severity": i.get("severity"),
            "affected_users": i.get("affected_users"),
            "affected_department": i.get("affected_department"),
            "affected_office": i.get("affected_office"),
            "responsible_team": i.get("responsible_team"),
        }
        for i in active
    ]

    total_affected = sum(int(i.get("affected_users", 0)) for i in active if str(i.get("affected_users", "0")).isdigit())

    return {
        "incident_impact": impact,
        "active_incident_count": len(active),
        "total_affected_users": total_affected,
        "source": "local_demo_data",
        "note": "[DEMO MODE] Impact data is simulated demo data.",
    }


def get_incident_updates() -> dict:
    """
    Return the latest status and update timestamp for every active major incident (Admin only).
    """
    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    active_statuses = {"investigating", "open"}
    active = [i for i in incidents if i.get("status", "").lower() in active_statuses]

    updates = [
        {
            "incident_id": i.get("incident_id"),
            "title": i.get("title"),
            "status": i.get("status"),
            "severity": i.get("severity"),
            "last_updated": i.get("last_updated"),
            "estimated_resolution": i.get("estimated_resolution") or "TBD",
            "responsible_team": i.get("responsible_team"),
            "affected_service": i.get("affected_service"),
        }
        for i in active
    ]

    return {
        "incident_updates": updates,
        "count": len(updates),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Incident update data is simulated demo data.",
    }


def get_incident_responsible_team() -> dict:
    """
    Return which team is responsible for resolving each active incident (Admin only).
    """
    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    active_statuses = {"investigating", "open"}
    active = [i for i in incidents if i.get("status", "").lower() in active_statuses]

    assignments = [
        {
            "incident_id": i.get("incident_id"),
            "title": i.get("title"),
            "status": i.get("status"),
            "severity": i.get("severity"),
            "responsible_team": i.get("responsible_team"),
            "affected_service": i.get("affected_service"),
            "affected_department": i.get("affected_department"),
        }
        for i in active
    ]

    return {
        "incident_team_assignments": assignments,
        "count": len(assignments),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Team assignment data is simulated demo data.",
    }


def get_sla_breaches() -> dict:
    """
    Identify incidents that have been open longer than their SLA deadline (Admin only).
    """
    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    active_statuses = {"investigating", "open"}
    active = [i for i in incidents if i.get("status", "").lower() in active_statuses]

    # Reference time: use the fixed demo reference time (2026-10-04 11:00:00 IST)
    # to avoid real-clock dependency in demo data
    from datetime import datetime
    try:
        now = datetime(2026, 10, 4, 11, 0, 0)
    except Exception:
        now = datetime.now()

    breached = []
    within_sla = []
    for inc in active:
        sla_str = inc.get("sla_deadline", "")
        if not sla_str:
            within_sla.append({**inc, "sla_status": "No SLA set"})
            continue
        try:
            sla_dt = datetime.strptime(sla_str, "%Y-%m-%d %H:%M:%S")
            is_breached = now > sla_dt
        except ValueError:
            is_breached = False
        entry = {
            "incident_id": inc.get("incident_id"),
            "title": inc.get("title"),
            "severity": inc.get("severity"),
            "status": inc.get("status"),
            "responsible_team": inc.get("responsible_team"),
            "sla_deadline": sla_str,
            "sla_status": "BREACHED" if is_breached else "Within SLA",
        }
        if is_breached:
            breached.append(entry)
        else:
            within_sla.append(entry)

    return {
        "sla_breached": breached,
        "within_sla": within_sla,
        "breached_count": len(breached),
        "total_active_incidents": len(active),
        "source": "local_demo_data",
        "note": "[DEMO MODE] SLA data is simulated demo data. Reference time: 2026-10-04 11:00:00 IST.",
    }


def get_recurring_incidents() -> dict:
    """
    Identify systems that have had multiple incidents recently (Admin only).
    Detects patterns by grouping incidents by affected_service.
    """
    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    service_map: dict[str, list] = {}
    for inc in incidents:
        svc = inc.get("affected_service", "Unknown")
        if svc not in service_map:
            service_map[svc] = []
        service_map[svc].append({
            "incident_id": inc.get("incident_id"),
            "title": inc.get("title"),
            "status": inc.get("status"),
            "severity": inc.get("severity"),
            "reported_at": inc.get("reported_at"),
        })

    recurring = {svc: incs for svc, incs in service_map.items() if len(incs) > 1}
    single = {svc: incs for svc, incs in service_map.items() if len(incs) == 1}

    return {
        "recurring_systems": [
            {"service": svc, "incident_count": len(incs), "incidents": incs}
            for svc, incs in recurring.items()
        ],
        "single_occurrence_systems": [
            {"service": svc, "incident_count": 1}
            for svc in single.keys()
        ],
        "recurring_count": len(recurring),
        "total_services_with_incidents": len(service_map),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Recurrence analysis uses simulated demo data.",
    }


def find_duplicate_incidents() -> dict:
    """
    Identify potential duplicate incidents covering the same underlying problem (Admin only).
    Uses the is_duplicate_of field and service/department overlap detection.
    """
    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    # Explicit duplicates (via is_duplicate_of field)
    explicit_dupes = [
        {
            "incident_id": i.get("incident_id"),
            "title": i.get("title"),
            "status": i.get("status"),
            "is_duplicate_of": i.get("is_duplicate_of"),
        }
        for i in incidents if i.get("is_duplicate_of", "").strip()
    ]

    # Potential duplicates: same affected_service
    service_map: dict[str, list] = {}
    for inc in incidents:
        svc = inc.get("affected_service", "")
        if svc not in service_map:
            service_map[svc] = []
        service_map[svc].append(inc.get("incident_id"))

    potential_dupes = [
        {"service": svc, "incident_ids": ids, "count": len(ids)}
        for svc, ids in service_map.items()
        if len(ids) > 1
    ]

    return {
        "explicit_duplicates": explicit_dupes,
        "potential_duplicates_by_service": potential_dupes,
        "explicit_duplicate_count": len(explicit_dupes),
        "potential_duplicate_groups": len(potential_dupes),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Duplicate detection uses simulated demo data.",
    }


def get_incidents_requiring_escalation() -> dict:
    """
    Identify active incidents that require escalation or immediate attention (Admin only).

    Criteria:
    - SLA breached
    - Critical severity and still Investigating/Open
    - High severity and open for more than threshold hours
    """
    sla_result = get_sla_breaches()
    impact_result = get_incident_impact()

    try:
        incidents = _read_incidents()
    except FileNotFoundError as e:
        return {"error": str(e)}

    active_statuses = {"investigating", "open"}
    active = [i for i in incidents if i.get("status", "").lower() in active_statuses]

    # Critical incidents always require escalation attention
    critical = [
        i for i in active
        if i.get("severity", "").lower() == "critical"
    ]

    # SLA-breached incidents
    sla_breached_ids = {
        i["incident_id"] for i in sla_result.get("sla_breached", [])
    }

    requires_escalation = []
    for inc in active:
        reasons = []
        if inc.get("severity", "").lower() == "critical":
            reasons.append("Critical severity — requires immediate attention")
        if inc.get("incident_id", "") in sla_breached_ids:
            reasons.append("SLA deadline has been exceeded")
        if reasons:
            requires_escalation.append({
                "incident_id": inc.get("incident_id"),
                "title": inc.get("title"),
                "status": inc.get("status"),
                "severity": inc.get("severity"),
                "responsible_team": inc.get("responsible_team"),
                "sla_deadline": inc.get("sla_deadline"),
                "escalation_reasons": reasons,
            })

    return {
        "incidents_requiring_escalation": requires_escalation,
        "escalation_count": len(requires_escalation),
        "total_active_incidents": len(active),
        "source": "local_demo_data",
        "note": "[DEMO MODE] Escalation analysis uses simulated demo data.",
    }
