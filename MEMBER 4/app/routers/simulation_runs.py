import math
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.auth import AuthUser, require_operator
from app.db import _sanitize_error, get_supabase_client
from app.schemas.simulation_run import (
    SimulationRunCreate,
    SimulationRunPagination,
    SimulationRunResponse,
    SimulationRunUpdate,
)

router = APIRouter(prefix="/simulation-runs", tags=["Simulation Runs"])


@router.get(
    "",
    response_model=SimulationRunPagination,
    summary="List simulation runs with pagination and filtering",
)
def list_simulation_runs(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    name: Optional[str] = Query(
        None, description="Filter runs by name substring"
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by execution status (e.g. pending, running, completed, failed)",
    ),
    start_date: Optional[datetime] = Query(
        None, description="Filter runs created on or after this timestamp"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter runs created on or before this timestamp"
    ),
    client=Depends(get_supabase_client),
) -> SimulationRunPagination:
    """
    Retrieve simulation run records with pagination.
    Supports filtering by name, status, and creation date window.
    """
    try:
        offset = (page - 1) * page_size
        query = client.table("simulation_runs").select("*", count="exact")

        if name:
            query = query.ilike("name", f"%{name.strip()}%")
        if status_filter:
            query = query.ilike("status", f"%{status_filter.strip()}%")
        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        if end_date:
            query = query.lte("created_at", end_date.isoformat())

        query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
        response = query.execute()

        total = response.count if response.count is not None else len(response.data or [])
        items = response.data or []
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return SimulationRunPagination(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query simulation runs: {_sanitize_error(exc)}",
        )


@router.get(
    "/{id}",
    response_model=SimulationRunResponse,
    summary="Retrieve a simulation run by UUID",
)
def get_simulation_run(
    id: UUID = Path(..., description="Unique simulation run UUID"),
    client=Depends(get_supabase_client),
) -> SimulationRunResponse:
    """Retrieve details for a single simulation run by its unique UUID."""
    try:
        response = (
            client.table("simulation_runs").select("*").eq("id", str(id)).limit(1).execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Simulation run with ID '{id}' not found.",
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve simulation run: {_sanitize_error(exc)}",
        )


@router.post(
    "",
    response_model=SimulationRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a simulation run record (Operator or Admin required)",
)
def create_simulation_run(
    payload: SimulationRunCreate,
    current_user: AuthUser = Depends(require_operator),
    client=Depends(get_supabase_client),
) -> SimulationRunResponse:
    """
    Register a new simulation run record to track orbital collision simulations.

    Requirements:
    - User must possess 'operator' or 'admin' role.
    - Stores initial configuration and parameters in input_data JSONB.
    """
    try:
        insert_data = payload.model_dump(mode="json")
        insert_res = client.table("simulation_runs").insert(insert_data).execute()
        if not insert_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Simulation run insertion succeeded but no record returned.",
            )
        return insert_res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create simulation run: {_sanitize_error(exc)}",
        )


@router.patch(
    "/{id}",
    response_model=SimulationRunResponse,
    summary="Update simulation run status and results (Operator or Admin required)",
)
def update_simulation_run(
    payload: SimulationRunUpdate,
    id: UUID = Path(..., description="Unique simulation run UUID to update"),
    current_user: AuthUser = Depends(require_operator),
    client=Depends(get_supabase_client),
) -> SimulationRunResponse:
    """
    Update a simulation run's execution status, parameters, or completed results.

    Requirements:
    - User must possess 'operator' or 'admin' role.
    - Simulation run must exist.
    """
    str_id = str(id)

    # 1. Verify simulation exists
    try:
        existing = (
            client.table("simulation_runs").select("*").eq("id", str_id).limit(1).execute()
        )
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Simulation run with ID '{id}' not found.",
            )
        current_record = existing.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Simulation lookup failed: {_sanitize_error(exc)}",
        )

    # 2. Extract update payload
    update_data = payload.model_dump(mode="json", exclude_unset=True)
    if not update_data:
        return current_record

    # 3. Apply update
    try:
        update_res = (
            client.table("simulation_runs").update(update_data).eq("id", str_id).execute()
        )
        if not update_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Simulation update operation succeeded but no record returned.",
            )
        return update_res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update simulation run: {_sanitize_error(exc)}",
        )
