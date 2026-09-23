"""
databricks/client.py
--------------------
Databricks connection client.

In DEMO_MODE=true  → returns None; callers fall back to local CSV data.
In DEMO_MODE=false → connects to Databricks SQL warehouse using OAuth.

Required env vars (when DEMO_MODE=false):
    DATABRICKS_SERVER_HOSTNAME  e.g. adb-xxxx.azuredatabricks.net
    DATABRICKS_HTTP_PATH        e.g. /sql/1.0/warehouses/abc123
    DATABRICKS_CATALOG          Unity Catalog catalog name
    DATABRICKS_SCHEMA           Schema inside the catalog

Authentication:
    Uses Databricks OAuth (auth_type="databricks-oauth").
    No token / PAT is required or supported.

NOTE: This module uses the 'databricks-sql-connector' package which is
      listed in requirements.txt but only needed when DEMO_MODE=false.
      It is imported lazily so DEMO_MODE=true works without the package.
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Connection cache ──────────────────────────────────────────────────────────
_connection = None


def is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "true").lower() == "true"


def get_connection():
    """
    Return a live Databricks SQL connection, or None if in DEMO_MODE.

    Uses OAuth authentication (auth_type="databricks-oauth").
    Caches the connection so we don't reconnect on every query.
    """
    global _connection

    if is_demo_mode():
        return None

    if _connection is not None:
        return _connection

    server_hostname = os.getenv("DATABRICKS_SERVER_HOSTNAME", "").strip()
    http_path = os.getenv("DATABRICKS_HTTP_PATH", "").strip()

    if not server_hostname or not http_path:
        raise ValueError(
            "Databricks configuration is incomplete. "
            "Set DATABRICKS_SERVER_HOSTNAME and DATABRICKS_HTTP_PATH "
            "in your .env file, or set DEMO_MODE=true to use local data."
        )

    try:
        # Lazy import — only needed when DEMO_MODE=false
        from databricks import sql as dbsql  # type: ignore

        _connection = dbsql.connect(
            server_hostname=server_hostname,
            http_path=http_path,
            auth_type="databricks-oauth",
        )
        logger.info("Connected to Databricks SQL warehouse via OAuth.")
        return _connection
    except ImportError:
        raise ImportError(
            "databricks-sql-connector is not installed. "
            "Run: pip install databricks-sql-connector"
        )
    except Exception as e:
        logger.error("Failed to connect to Databricks: %s", e)
        raise


def get_catalog() -> str:
    return os.getenv("DATABRICKS_CATALOG", "main")


def get_schema() -> str:
    return os.getenv("DATABRICKS_SCHEMA", "acme_company")


def get_full_table(table: str) -> str:
    """Return fully-qualified Unity Catalog table name: catalog.schema.table"""
    return f"{get_catalog()}.{get_schema()}.{table}"


def close_connection():
    """Close and reset the cached connection."""
    global _connection
    if _connection is not None:
        try:
            _connection.close()
        except Exception:
            pass
        _connection = None
        logger.info("Databricks connection closed.")
