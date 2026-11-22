import math
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.auth import AuthUser, require_admin, require_operator
from app.db import _sanitize_error, get_supabase_client
from app.schemas.satellite import (
    SatelliteCreate,
    SatellitePagination,
    SatelliteResponse,
    SatelliteUpdate,
)

router = APIRouter(prefix="/satellites", tags=["Satellites"])


def _handle_db_exception(exc: Exception, norad_id: Optional[int] = None) -> None:
    """Helper to translate database errors into appropriate HTTP exceptions."""
    err_msg = str(exc)
    err_lower = err_msg.lower()
    if (
        "23505" in err_msg
        or "duplicate key" in err_lower
        or "unique constraint" in err_lower
        or "norad_id" in err_lower
    ):
        target = f" {norad_id}" if norad_id is not None else ""
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Satellite with NORAD ID{target} already exists.",
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Database operation failed: {_sanitize_error(exc)}",
    )


@router.get(
    "",
    response_model=SatellitePagination,
    summary="List all registered satellites with pagination",
)
def list_satellites(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by operational status (e.g. ACTIVE)"
    ),
    operator_name: Optional[str] = Query(
        None, description="Filter by operator name substring"
    ),
    client=Depends(get_supabase_client),
) -> SatellitePagination:
    """
    Retrieve all registered satellites with pagination.
    Supports filtering by status and operator name.
    """
    try:
        offset = (page - 1) * page_size
        query = client.table("satellites").select("*", count="exact")

        if status_filter:
            query = query.ilike("status", f"%{status_filter.strip()}%")
        if operator_name:
            query = query.ilike("operator_name", f"%{operator_name.strip()}%")

        # Supabase .range() is zero-based and end-inclusive: [offset, offset + page_size - 1]
        query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
        response = query.execute()

        total = response.count if response.count is not None else len(response.data or [])
        items = response.data or []
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return SatellitePagination(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query satellites: {_sanitize_error(exc)}",
        )


@router.get(
    "/{id}",
    response_model=SatelliteResponse,
    summary="Retrieve satellite details by UUID",
)
def get_satellite(
    id: UUID = Path(..., description="Unique satellite UUID"),
    client=Depends(get_supabase_client),
) -> SatelliteResponse:
    """Retrieve a single satellite record by its unique UUID."""
    try:
        response = client.table("satellites").select("*").eq("id", str(id)).limit(1).execute()
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Satellite with ID '{id}' not found.",
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve satellite: {_sanitize_error(exc)}",
        )


@router.post(
    "",
    response_model=SatelliteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new satellite (Operator or Admin required)",
)
def create_satellite(
    payload: SatelliteCreate,
    current_user: AuthUser = Depends(require_operator),
    client=Depends(get_supabase_client),
) -> SatelliteResponse:
    """
    Register a new satellite record.
    Requires an authenticated user with 'operator' or 'admin' role.
    Validates payload and prevents duplicate NORAD IDs.
    """
    # 1. Proactive check for duplicate NORAD ID
    try:
        existing = (
            client.table("satellites")
            .select("id")
            .eq("norad_id", payload.norad_id)
            .limit(1)
            .execute()
        )
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Satellite with NORAD ID {payload.norad_id} already exists.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        _handle_db_exception(exc, payload.norad_id)

    # 2. Insert satellite record
    try:
        data_to_insert = payload.model_dump()
        insert_res = client.table("satellites").insert(data_to_insert).execute()
        if not insert_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Satellite insertion completed but no data returned from database.",
            )
        return insert_res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        _handle_db_exception(exc, payload.norad_id)


@router.patch(
    "/{id}",
    response_model=SatelliteResponse,
    summary="Update satellite information (Operator or Admin required)",
)
def update_satellite(
    payload: SatelliteUpdate,
    id: UUID = Path(..., description="Unique satellite UUID to update"),
    current_user: AuthUser = Depends(require_operator),
    client=Depends(get_supabase_client),
) -> SatelliteResponse:
    """
    Update satellite attributes (name, operator_name, status, or norad_id).
    Requires an authenticated user with 'operator' or 'admin' role.
    Validates record existence and detects duplicate NORAD conflicts.
    """
    str_id = str(id)

    # 1. Check if satellite exists
    try:
        existing = client.table("satellites").select("*").eq("id", str_id).limit(1).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Satellite with ID '{id}' not found.",
            )
        current_record = existing.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database lookup failed: {_sanitize_error(exc)}",
        )

    # 2. If norad_id is being updated, verify it doesn't conflict with another satellite
    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        return current_record

    new_norad_id = update_data.get("norad_id")
    if new_norad_id is not None and new_norad_id != current_record.get("norad_id"):
        try:
            conflict = (
                client.table("satellites")
                .select("id")
                .eq("norad_id", new_norad_id)
                .neq("id", str_id)
                .limit(1)
                .execute()
            )
            if conflict.data:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Satellite with NORAD ID {new_norad_id} already exists.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            _handle_db_exception(exc, new_norad_id)

    # 3. Apply update
    try:
        update_res = client.table("satellites").update(update_data).eq("id", str_id).execute()
        if not update_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Update operation succeeded but no record returned.",
            )
        return update_res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        _handle_db_exception(exc, new_norad_id)


@router.delete(
    "/{id}",
    summary="Delete satellite (Administrator authorization required)",
)
def delete_satellite(
    id: UUID = Path(..., description="Unique satellite UUID to delete"),
    current_user: AuthUser = Depends(require_admin),
    client=Depends(get_supabase_client),
) -> Dict[str, Any]:
    """
    Permanently delete a satellite record.
    CRITICAL: Strictly requires 'admin' role. Operator role is forbidden.
    """
    str_id = str(id)

    # 1. Verify existence before deletion
    try:
        existing = client.table("satellites").select("id").eq("id", str_id).limit(1).execute()
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Satellite with ID '{id}' not found.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database lookup failed: {_sanitize_error(exc)}",
        )

    # 2. Perform deletion
    try:
        client.table("satellites").delete().eq("id", str_id).execute()
        return {
            "message": f"Satellite with ID '{id}' successfully deleted.",
            "id": str_id,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete satellite: {_sanitize_error(exc)}",
        )
