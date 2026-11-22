import math
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.auth import AuthUser, require_operator
from app.db import _sanitize_error, get_supabase_client
from app.schemas.sustainability_metric import (
    SustainabilityMetricCreate,
    SustainabilityMetricPagination,
    SustainabilityMetricResponse,
    SustainabilityMetricUpdate,
)

router = APIRouter(prefix="/sustainability-metrics", tags=["Sustainability Metrics"])


@router.get(
    "",
    response_model=SustainabilityMetricPagination,
    summary="List sustainability metrics with pagination and filtering",
)
def list_sustainability_metrics(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    simulation_id: Optional[UUID] = Query(
        None, description="Filter metrics by associated simulation run UUID"
    ),
    min_avoided_approaches: Optional[int] = Query(
        None,
        ge=0,
        description="Filter records with avoided_close_approaches >= min_avoided_approaches",
    ),
    min_fuel_saved: Optional[float] = Query(
        None,
        ge=0.0,
        description="Filter records with estimated_fuel_saved (kg) >= min_fuel_saved",
    ),
    max_delta_v: Optional[float] = Query(
        None,
        ge=0.0,
        description="Filter records with total_delta_v <= max_delta_v",
    ),
    start_date: Optional[datetime] = Query(
        None, description="Filter records created on or after this timestamp"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Filter records created on or before this timestamp"
    ),
    client=Depends(get_supabase_client),
) -> SustainabilityMetricPagination:
    """
    Retrieve sustainability metrics with pagination.
    Supports filtering by simulation run, fuel saved, delta-v expenditure, and avoided close approaches.
    """
    try:
        offset = (page - 1) * page_size
        query = client.table("sustainability_metrics").select("*", count="exact")

        if simulation_id:
            query = query.eq("simulation_id", str(simulation_id))
        if min_avoided_approaches is not None:
            query = query.gte("avoided_close_approaches", min_avoided_approaches)
        if min_fuel_saved is not None:
            query = query.gte("estimated_fuel_saved", min_fuel_saved)
        if max_delta_v is not None:
            query = query.lte("total_delta_v", max_delta_v)
        if start_date:
            query = query.gte("created_at", start_date.isoformat())
        if end_date:
            query = query.lte("created_at", end_date.isoformat())

        query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
        response = query.execute()

        total = response.count if response.count is not None else len(response.data or [])
        items = response.data or []
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return SustainabilityMetricPagination(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query sustainability metrics: {_sanitize_error(exc)}",
        )


@router.get(
    "/{id}",
    response_model=SustainabilityMetricResponse,
    summary="Retrieve a sustainability metric record by UUID",
)
def get_sustainability_metric(
    id: UUID = Path(..., description="Unique sustainability metric UUID"),
    client=Depends(get_supabase_client),
) -> SustainabilityMetricResponse:
    """Retrieve details for a single sustainability metric record by its unique UUID."""
    try:
        response = (
            client.table("sustainability_metrics").select("*").eq("id", str(id)).limit(1).execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sustainability metric with ID '{id}' not found.",
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sustainability metric: {_sanitize_error(exc)}",
        )


@router.post(
    "",
    response_model=SustainabilityMetricResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a sustainability metric (Operator or Admin required)",
)
def create_sustainability_metric(
    payload: SustainabilityMetricCreate,
    current_user: AuthUser = Depends(require_operator),
    client=Depends(get_supabase_client),
) -> SustainabilityMetricResponse:
    """
    Store a new sustainability metric calculated from an orbital simulation or avoidance plan.

    Requirements:
    - User must possess 'operator' or 'admin' role.
    - If provided, referenced simulation_id must exist in public.simulation_runs.
    """
    # 1. If simulation_id is provided, verify simulation run exists
    if payload.simulation_id:
        try:
            sim_check = (
                client.table("simulation_runs")
                .select("id")
                .eq("id", str(payload.simulation_id))
                .limit(1)
                .execute()
            )
            if not sim_check.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Referenced simulation run with ID '{payload.simulation_id}' does not exist.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Simulation run verification failed: {_sanitize_error(exc)}",
            )

    # 2. Insert sustainability metric record
    try:
        insert_data = payload.model_dump(mode="json")
        insert_res = client.table("sustainability_metrics").insert(insert_data).execute()
        if not insert_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Sustainability metric insertion succeeded but no record returned.",
            )
        return insert_res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record sustainability metric: {_sanitize_error(exc)}",
        )


@router.patch(
    "/{id}",
    response_model=SustainabilityMetricResponse,
    summary="Update an existing sustainability metric (Operator or Admin required)",
)
def update_sustainability_metric(
    payload: SustainabilityMetricUpdate,
    id: UUID = Path(..., description="Unique sustainability metric UUID to update"),
    current_user: AuthUser = Depends(require_operator),
    client=Depends(get_supabase_client),
) -> SustainabilityMetricResponse:
    """
    Update sustainability metrics (simulation_id, total_delta_v, estimated_fuel_saved, or avoided_close_approaches).

    Requirements:
    - User must possess 'operator' or 'admin' role.
    - Metric record must exist.
    - If updating simulation_id, referenced simulation run must exist.
    """
    str_id = str(id)

    # 1. Verify sustainability metric exists
    try:
        existing = (
            client.table("sustainability_metrics").select("*").eq("id", str_id).limit(1).execute()
        )
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sustainability metric with ID '{id}' not found.",
            )
        current_record = existing.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Metric lookup failed: {_sanitize_error(exc)}",
        )

    # 2. Extract update payload
    update_data = payload.model_dump(mode="json", exclude_unset=True)
    if not update_data:
        return current_record

    # 3. If simulation_id is updated, verify it exists
    new_sim_id = update_data.get("simulation_id")
    if new_sim_id and new_sim_id != current_record.get("simulation_id"):
        try:
            sim_check = (
                client.table("simulation_runs")
                .select("id")
                .eq("id", new_sim_id)
                .limit(1)
                .execute()
            )
            if not sim_check.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Referenced simulation run with ID '{new_sim_id}' does not exist.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Simulation run verification failed: {_sanitize_error(exc)}",
            )

    # 4. Apply update
    try:
        update_res = (
            client.table("sustainability_metrics").update(update_data).eq("id", str_id).execute()
        )
        if not update_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Sustainability metric update succeeded but no record returned.",
            )
        return update_res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sustainability metric: {_sanitize_error(exc)}",
        )
