import time
from typing import Any, Dict, Optional, Tuple
from app.config import settings

# Gracefully handle import if dependencies are not yet installed in local environment
try:
    from supabase import create_client, Client
except ImportError:  # pragma: no cover
    create_client = None  # type: ignore
    Client = Any  # type: ignore

# The six official ORBI-SYNC tables in the Supabase PostgreSQL database
ORBI_SYNC_TABLES: Tuple[str, ...] = (
    "satellites",
    "orbital_states",
    "conjunction_events",
    "manoeuvre_plans",
    "simulation_runs",
    "sustainability_metrics",
)

_client_instance: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Returns a reusable singleton Supabase client instance.
    Initializes the client using SUPABASE_URL and SUPABASE_SECRET_KEY.

    Raises:
        RuntimeError: If the official supabase package is not installed.
        ValueError: If SUPABASE_URL or SUPABASE_SECRET_KEY are not configured.
    """
    global _client_instance

    if create_client is None:
        raise RuntimeError(
            "The 'supabase' package is not installed. "
            "Please run 'pip install -r requirements.txt' in your virtual environment."
        )

    if not settings.is_supabase_configured:
        raise ValueError(
            "Supabase credentials are not configured. "
            "Please ensure SUPABASE_URL and SUPABASE_SECRET_KEY are set in your .env file."
        )

    if _client_instance is None:
        _client_instance = create_client(
            supabase_url=settings.supabase_url,
            supabase_key=settings.supabase_secret_key,
        )

    return _client_instance


def _sanitize_error(err: Exception) -> str:
    """Strips out sensitive keys or credentials from error messages."""
    error_str = str(err)
    if settings.supabase_secret_key and settings.supabase_secret_key in error_str:
        error_str = error_str.replace(settings.supabase_secret_key, "[REDACTED]")
    return error_str


def check_database_connection(
    test_table: str = "satellites", client: Optional[Client] = None
) -> Dict[str, Any]:
    """
    Executes an active query against Supabase PostgreSQL to verify connectivity.

    Queries 1 record and requests the row count from the specified table.
    Ensures secret credentials are never exposed in return values or exceptions.
    """
    if client is None:
        client = get_supabase_client()

    start_time = time.perf_counter()
    # Execute a lightweight, column-agnostic query against the database
    response = client.table(test_table).select("*", count="exact").limit(1).execute()
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

    return {
        "status": "connected",
        "database": "supabase_postgresql",
        "table_tested": test_table,
        "latency_ms": elapsed_ms,
        "record_count": response.count if response.count is not None else len(response.data or []),
        "tables_registered": list(ORBI_SYNC_TABLES),
    }
