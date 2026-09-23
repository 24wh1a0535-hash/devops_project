"""
databricks/queries.py
---------------------
Parameterised SQL queries for Databricks Unity Catalog tables.

These functions run against real Databricks tables when DEMO_MODE=false.
They use parameterised queries — no raw string interpolation — to prevent
SQL injection.

Table structure expected in Unity Catalog:
    {catalog}.{schema}.employees
    {catalog}.{schema}.departments
    {catalog}.{schema}.projects

See databricks/setup.sql for the CREATE TABLE statements.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _run_query(connection, sql: str, params: tuple = ()) -> list[dict]:
    """
    Execute a parameterised SQL query and return rows as list of dicts.

    Args:
        connection: Active Databricks SQL connection.
        sql: SQL string with %s placeholders.
        params: Tuple of values to bind.

    Returns:
        List of row dicts.
    """
    try:
        cursor = connection.cursor()
        cursor.execute(sql, params)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        cursor.close()
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error("Databricks query failed: %s | SQL: %s", e, sql)
        raise


def query_employees(
    connection,
    catalog: str,
    schema: str,
    department: Optional[str] = None,
    employee_id: Optional[str] = None,
) -> list[dict]:
    """Fetch employees from Unity Catalog, optionally filtered."""
    table = f"`{catalog}`.`{schema}`.`employees`"

    if employee_id:
        sql = f"SELECT * FROM {table} WHERE employee_id = %s"
        return _run_query(connection, sql, (employee_id,))
    elif department:
        sql = f"SELECT * FROM {table} WHERE LOWER(department) = LOWER(%s)"
        return _run_query(connection, sql, (department,))
    else:
        sql = f"SELECT * FROM {table}"
        return _run_query(connection, sql)


def query_departments(
    connection,
    catalog: str,
    schema: str,
    department_name: Optional[str] = None,
) -> list[dict]:
    """Fetch departments from Unity Catalog, optionally filtered."""
    table = f"`{catalog}`.`{schema}`.`departments`"

    if department_name:
        sql = f"SELECT * FROM {table} WHERE LOWER(department_name) = LOWER(%s)"
        return _run_query(connection, sql, (department_name,))
    else:
        sql = f"SELECT * FROM {table}"
        return _run_query(connection, sql)


def query_projects(
    connection,
    catalog: str,
    schema: str,
    project_id: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict]:
    """Fetch projects from Unity Catalog, optionally filtered."""
    table = f"`{catalog}`.`{schema}`.`projects`"
    conditions = []
    params = []

    if project_id:
        conditions.append("project_id = %s")
        params.append(project_id)
    if department:
        conditions.append("LOWER(department) = LOWER(%s)")
        params.append(department)
    if status:
        conditions.append("LOWER(status) = LOWER(%s)")
        params.append(status)

    where = f" WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"SELECT * FROM {table}{where}"
    return _run_query(connection, sql, tuple(params))
