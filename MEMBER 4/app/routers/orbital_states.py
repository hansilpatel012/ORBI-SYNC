import math
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.auth import AuthUser, require_operator
from app.db import _sanitize_error, get_supabase_client
from app.schemas.orbital_state import (
    OrbitalStateCreate,
    OrbitalStatePagination,
    OrbitalStateResponse,
)

router = APIRouter(prefix="/orbital-states", tags=["Orbital States"])


@router.get(
    "",
    response_model=OrbitalStatePagination,
    summary="List orbital states with pagination and satellite filtering",
)
def list_orbital_states(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    satellite_id: Optional[UUID] = Query(
        None, description="Filter states by specific satellite UUID"
    ),
    start_epoch: Optional[datetime] = Query(
        None, description="Filter states with epoch greater than or equal to timestamp"
    ),
    end_epoch: Optional[datetime] = Query(
        None, description="Filter states with epoch less than or equal to timestamp"
    ),
    client=Depends(get_supabase_client),
) -> OrbitalStatePagination:
    """
    Retrieve orbital state records with pagination.
    Supports filtering by satellite UUID and epoch time window.
    """
    try:
        offset = (page - 1) * page_size
        query = client.table("orbital_states").select("*", count="exact")

        if satellite_id:
            query = query.eq("satellite_id", str(satellite_id))
        if start_epoch:
            query = query.gte("epoch", start_epoch.isoformat())
        if end_epoch:
            query = query.lte("epoch", end_epoch.isoformat())

        query = query.order("epoch", desc=True).range(offset, offset + page_size - 1)
        response = query.execute()

        total = response.count if response.count is not None else len(response.data or [])
        items = response.data or []
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return OrbitalStatePagination(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query orbital states: {_sanitize_error(exc)}",
        )


@router.get(
    "/{id}",
    response_model=OrbitalStateResponse,
    summary="Retrieve an orbital state by UUID",
)
def get_orbital_state(
    id: UUID = Path(..., description="Unique orbital state UUID"),
    client=Depends(get_supabase_client),
) -> OrbitalStateResponse:
    """Retrieve a single orbital state record by its unique UUID."""
    try:
        response = (
            client.table("orbital_states").select("*").eq("id", str(id)).limit(1).execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Orbital state with ID '{id}' not found.",
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve orbital state: {_sanitize_error(exc)}",
        )


@router.post(
    "",
    response_model=OrbitalStateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a propagated orbital state (Operator or Admin required)",
)
def create_orbital_state(
    payload: OrbitalStateCreate,
    current_user: AuthUser = Depends(require_operator),
    client=Depends(get_supabase_client),
) -> OrbitalStateResponse:
    """
    Store a newly propagated orbital state vector from the SGP4 propagation module.

    Requirements:
    - User must possess 'operator' or 'admin' role.
    - Referenced satellite must exist in public.satellites.
    - Coordinates and velocities are validated against the database schema.
    """
    # 1. Validate that the referenced satellite exists in public.satellites
    try:
        sat_check = (
            client.table("satellites")
            .select("id")
            .eq("id", str(payload.satellite_id))
            .limit(1)
            .execute()
        )
        if not sat_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referenced satellite with ID '{payload.satellite_id}' does not exist.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Satellite verification failed: {_sanitize_error(exc)}",
        )

    # 2. Insert orbital state record
    try:
        # mode="json" converts UUIDs to strings and datetimes to ISO-8601 strings
        insert_data = payload.model_dump(mode="json")
        insert_res = client.table("orbital_states").insert(insert_data).execute()
        if not insert_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Orbital state insertion succeeded but no data returned from database.",
            )
        return insert_res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record orbital state: {_sanitize_error(exc)}",
        )
