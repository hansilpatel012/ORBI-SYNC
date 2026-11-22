from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Security, status
from fastapi.security.api_key import APIKeyHeader

from app.config import settings
from app.db import _sanitize_error, check_database_connection, get_supabase_client

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

diagnostic_key_header = APIKeyHeader(name="X-Diagnostic-Key", auto_error=False)


def verify_diagnostic_access(
    api_key: Optional[str] = Security(diagnostic_key_header),
) -> bool:
    """
    Protects internal database diagnostics from public exposure.

    Security Policies:
    1. If DIAGNOSTIC_API_KEY is configured in .env, strictly require matching X-Diagnostic-Key.
    2. If running in 'production' and DIAGNOSTIC_API_KEY is unset, block access (HTTP 403)
       to avoid exposing database internals to public clients.
    3. In 'development' or 'local' environments without DIAGNOSTIC_API_KEY, allow direct access.
    """
    configured_key = settings.diagnostic_api_key
    env = settings.environment

    if configured_key:
        if not api_key or api_key != configured_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized: Missing or invalid 'X-Diagnostic-Key' header.",
            )
        return True

    if env == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Database diagnostics are disabled in production until DIAGNOSTIC_API_KEY is configured.",
        )

    return True


@router.get("", summary="Basic service liveness probe")
def health_check() -> Dict[str, str]:
    """Basic liveness probe endpoint returning service operational status."""
    return {"status": "ok"}


@router.get(
    "/database",
    summary="Supabase PostgreSQL connectivity check",
    dependencies=[Depends(verify_diagnostic_access)],
)
def database_health_check(
    response: Response, client=Depends(get_supabase_client)
) -> Dict[str, Any]:
    """
    Performs an active database query against the ORBI-SYNC Supabase PostgreSQL instance.

    Protected before public deployment via X-Diagnostic-Key / production guard.
    Never exposes database passwords, secret keys, or raw connection strings.
    """
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

    try:
        diagnostic_result = check_database_connection(client=client)
        return diagnostic_result
    except (ValueError, RuntimeError) as config_err:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "supabase_postgresql",
                "error": str(config_err),
            },
        )
    except Exception as exc:
        sanitized_msg = _sanitize_error(exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "database": "supabase_postgresql",
                "error": f"Database connectivity check failed: {sanitized_msg}",
            },
        )
