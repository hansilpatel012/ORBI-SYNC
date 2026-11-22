import math
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.auth import AuthUser, require_operator
from app.db import _sanitize_error, get_supabase_client
from app.schemas.manoeuvre_plan import (
    ManoeuvrePlanCreate,
    ManoeuvrePlanPagination,
    ManoeuvrePlanResponse,
    ManoeuvrePlanUpdate,
)

router = APIRouter(prefix="/manoeuvre-plans", tags=["Manoeuvre Plans"])


@router.get(
    "",
    response_model=ManoeuvrePlanPagination,
    summary="List manoeuvre plans with pagination and filtering",
)
def list_manoeuvre_plans(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    satellite_id: Optional[UUID] = Query(
        None, description="Filter plans by maneuvering satellite UUID"
    ),
    conjunction_id: Optional[UUID] = Query(
        None, description="Filter plans by mitigated conjunction event UUID"
    ),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by plan status (e.g. proposed, approved, executing, completed, cancelled)",
    ),
    start_time: Optional[datetime] = Query(
        None, description="Filter plans with proposed_time >= start_time"
    ),
    end_time: Optional[datetime] = Query(
        None, description="Filter plans with proposed_time <= end_time"
    ),
    client=Depends(get_supabase_client),
) -> ManoeuvrePlanPagination:
    """
    Retrieve collision avoidance manoeuvre plans with pagination.
    Supports filtering by satellite, conjunction event, status, and execution window.
    """
    try:
        offset = (page - 1) * page_size
        query = client.table("manoeuvre_plans").select("*", count="exact")

        if satellite_id:
            query = query.eq("satellite_id", str(satellite_id))
        if conjunction_id:
            query = query.eq("conjunction_id", str(conjunction_id))
        if status_filter:
            query = query.ilike("status", f"%{status_filter.strip()}%")
        if start_time:
            query = query.gte("proposed_time", start_time.isoformat())
        if end_time:
            query = query.lte("proposed_time", end_time.isoformat())

        query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
        response = query.execute()

        total = response.count if response.count is not None else len(response.data or [])
        items = response.data or []
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return ManoeuvrePlanPagination(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query manoeuvre plans: {_sanitize_error(exc)}",
        )


@router.get(
    "/{id}",
    response_model=ManoeuvrePlanResponse,
    summary="Retrieve a manoeuvre plan by UUID",
)
def get_manoeuvre_plan(
    id: UUID = Path(..., description="Unique manoeuvre plan UUID"),
    client=Depends(get_supabase_client),
) -> ManoeuvrePlanResponse:
    """Retrieve details for a single manoeuvre plan by its unique UUID."""
    try:
        response = (
            client.table("manoeuvre_plans").select("*").eq("id", str(id)).limit(1).execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manoeuvre plan with ID '{id}' not found.",
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve manoeuvre plan: {_sanitize_error(exc)}",
        )


@router.post(
    "",
    response_model=ManoeuvrePlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a manoeuvre plan (Operator or Admin required)",
)
def create_manoeuvre_plan(
    payload: ManoeuvrePlanCreate,
    current_user: AuthUser = Depends(require_operator),
    client=Depends(get_supabase_client),
) -> ManoeuvrePlanResponse:
    """
    Create a new collision avoidance or orbit correction manoeuvre plan.

    Requirements:
    - User must possess 'operator' or 'admin' role.
    - Referenced satellite must exist in public.satellites.
    - If provided, referenced conjunction event must exist in public.conjunction_events.
    """
    # 1. Verify maneuvering satellite exists
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

    # 2. If conjunction_id is provided, verify conjunction event exists
    if payload.conjunction_id:
        try:
            conj_check = (
                client.table("conjunction_events")
                .select("id")
                .eq("id", str(payload.conjunction_id))
                .limit(1)
                .execute()
            )
            if not conj_check.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Referenced conjunction event with ID '{payload.conjunction_id}' does not exist.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Conjunction event verification failed: {_sanitize_error(exc)}",
            )

    # 3. Insert manoeuvre plan record
    try:
        insert_data = payload.model_dump(mode="json")
        insert_res = client.table("manoeuvre_plans").insert(insert_data).execute()
        if not insert_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Manoeuvre plan insertion succeeded but no record returned.",
            )
        return insert_res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record manoeuvre plan: {_sanitize_error(exc)}",
        )


@router.patch(
    "/{id}",
    response_model=ManoeuvrePlanResponse,
    summary="Update a manoeuvre plan (Operator or Admin required)",
)
def update_manoeuvre_plan(
    payload: ManoeuvrePlanUpdate,
    id: UUID = Path(..., description="Unique manoeuvre plan UUID to update"),
    current_user: AuthUser = Depends(require_operator),
    client=Depends(get_supabase_client),
) -> ManoeuvrePlanResponse:
    """
    Update an existing manoeuvre plan (status, delta_v, fuel_estimate, proposed_time, or conjunction_id).

    Requirements:
    - User must possess 'operator' or 'admin' role.
    - Plan must exist.
    - If updating conjunction_id, referenced conjunction event must exist.
    """
    str_id = str(id)

    # 1. Verify manoeuvre plan exists
    try:
        existing = (
            client.table("manoeuvre_plans").select("*").eq("id", str_id).limit(1).execute()
        )
        if not existing.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manoeuvre plan with ID '{id}' not found.",
            )
        current_record = existing.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan lookup failed: {_sanitize_error(exc)}",
        )

    # 2. Extract update payload
    update_data = payload.model_dump(mode="json", exclude_unset=True)
    if not update_data:
        return current_record

    # 3. If conjunction_id is updated, verify it exists
    new_conj_id = update_data.get("conjunction_id")
    if new_conj_id and new_conj_id != current_record.get("conjunction_id"):
        try:
            conj_check = (
                client.table("conjunction_events")
                .select("id")
                .eq("id", new_conj_id)
                .limit(1)
                .execute()
            )
            if not conj_check.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Referenced conjunction event with ID '{new_conj_id}' does not exist.",
                )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Conjunction event verification failed: {_sanitize_error(exc)}",
            )

    # 4. Apply update
    try:
        update_res = (
            client.table("manoeuvre_plans").update(update_data).eq("id", str_id).execute()
        )
        if not update_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Update operation succeeded but no record returned.",
            )
        return update_res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update manoeuvre plan: {_sanitize_error(exc)}",
        )
