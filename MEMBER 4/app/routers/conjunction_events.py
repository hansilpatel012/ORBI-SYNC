import math
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

from app.auth import AuthUser, require_operator
from app.db import _sanitize_error, get_supabase_client
from app.schemas.conjunction_event import (
    ConjunctionEventCreate,
    ConjunctionEventPagination,
    ConjunctionEventResponse,
)

router = APIRouter(prefix="/conjunction-events", tags=["Conjunction Events"])


def _assess_risk_level(
    miss_distance_km: Optional[float],
    collision_probability: Optional[float],
    provided_risk: Optional[str],
) -> str:
    """Helper to derive a standard risk tier if the client supplied 'unknown' or empty."""
    if provided_risk and provided_risk.strip().lower() != "unknown":
        return provided_risk.strip().lower()

    if collision_probability is not None:
        if collision_probability >= 1e-4:
            return "critical"
        if collision_probability >= 1e-5:
            return "high"
        if collision_probability >= 1e-6:
            return "medium"
        return "low"

    if miss_distance_km is not None:
        if miss_distance_km < 1.0:
            return "critical"
        if miss_distance_km < 5.0:
            return "high"
        if miss_distance_km < 25.0:
            return "medium"
        return "low"

    return "unknown"


@router.get(
    "",
    response_model=ConjunctionEventPagination,
    summary="List conjunction events with pagination and filtering",
)
def list_conjunction_events(
    page: int = Query(1, ge=1, description="Page number starting at 1"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    satellite_id: Optional[UUID] = Query(
        None, description="Filter events involving this satellite (either as primary or secondary)"
    ),
    satellite_1_id: Optional[UUID] = Query(
        None, description="Filter specifically by primary satellite UUID"
    ),
    satellite_2_id: Optional[UUID] = Query(
        None, description="Filter specifically by secondary satellite UUID"
    ),
    risk_level: Optional[str] = Query(
        None, description="Filter by risk tier (e.g. low, medium, high, critical)"
    ),
    status_filter: Optional[str] = Query(
        None, alias="status", description="Filter by resolution state (e.g. detected, monitoring, mitigated)"
    ),
    max_miss_distance_km: Optional[float] = Query(
        None, ge=0.0, description="Filter events with miss_distance_km <= max_miss_distance_km"
    ),
    min_collision_probability: Optional[float] = Query(
        None, ge=0.0, le=1.0, description="Filter events with collision_probability >= min_collision_probability"
    ),
    start_tca: Optional[datetime] = Query(
        None, description="Filter events with closest_approach (TCA) >= start_tca"
    ),
    end_tca: Optional[datetime] = Query(
        None, description="Filter events with closest_approach (TCA) <= end_tca"
    ),
    client=Depends(get_supabase_client),
) -> ConjunctionEventPagination:
    """
    Retrieve conjunction events with pagination and comprehensive filtering.
    Enables tracking of high-risk satellite close approaches and collision warnings.
    """
    try:
        offset = (page - 1) * page_size
        query = client.table("conjunction_events").select("*", count="exact")

        if satellite_id:
            query = query.or_(
                f"satellite_1_id.eq.{satellite_id},satellite_2_id.eq.{satellite_id}"
            )
        if satellite_1_id:
            query = query.eq("satellite_1_id", str(satellite_1_id))
        if satellite_2_id:
            query = query.eq("satellite_2_id", str(satellite_2_id))
        if risk_level:
            query = query.ilike("risk_level", f"%{risk_level.strip()}%")
        if status_filter:
            query = query.ilike("status", f"%{status_filter.strip()}%")
        if max_miss_distance_km is not None:
            query = query.lte("miss_distance_km", max_miss_distance_km)
        if min_collision_probability is not None:
            query = query.gte("collision_probability", min_collision_probability)
        if start_tca:
            query = query.gte("closest_approach", start_tca.isoformat())
        if end_tca:
            query = query.lte("closest_approach", end_tca.isoformat())

        query = query.order("created_at", desc=True).range(offset, offset + page_size - 1)
        response = query.execute()

        total = response.count if response.count is not None else len(response.data or [])
        items = response.data or []
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return ConjunctionEventPagination(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query conjunction events: {_sanitize_error(exc)}",
        )


@router.get(
    "/{id}",
    response_model=ConjunctionEventResponse,
    summary="Retrieve a conjunction event by UUID",
)
def get_conjunction_event(
    id: UUID = Path(..., description="Unique conjunction event UUID"),
    client=Depends(get_supabase_client),
) -> ConjunctionEventResponse:
    """Retrieve details for a single conjunction / close approach event by UUID."""
    try:
        response = (
            client.table("conjunction_events").select("*").eq("id", str(id)).limit(1).execute()
        )
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conjunction event with ID '{id}' not found.",
            )
        return response.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve conjunction event: {_sanitize_error(exc)}",
        )


@router.post(
    "",
    response_model=ConjunctionEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a conjunction prediction (Operator or Admin required)",
)
def create_conjunction_event(
    payload: ConjunctionEventCreate,
    current_user: AuthUser = Depends(require_operator),
    client=Depends(get_supabase_client),
) -> ConjunctionEventResponse:
    """
    Store a newly calculated satellite conjunction event / collision prediction.

    Requirements:
    - User must possess 'operator' or 'admin' role.
    - satellite_1_id and satellite_2_id must reference distinct existing satellites.
    - Automatic risk tier assessment is performed if risk_level is 'unknown'.
    """
    str_sat1 = str(payload.satellite_1_id)
    str_sat2 = str(payload.satellite_2_id)

    # 1. Verify primary satellite exists
    try:
        sat1_check = (
            client.table("satellites").select("id").eq("id", str_sat1).limit(1).execute()
        )
        if not sat1_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referenced primary satellite with ID '{payload.satellite_1_id}' does not exist.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Primary satellite verification failed: {_sanitize_error(exc)}",
        )

    # 2. Verify secondary satellite exists
    try:
        sat2_check = (
            client.table("satellites").select("id").eq("id", str_sat2).limit(1).execute()
        )
        if not sat2_check.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Referenced secondary satellite with ID '{payload.satellite_2_id}' does not exist.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Secondary satellite verification failed: {_sanitize_error(exc)}",
        )

    # 3. Assess risk level if needed
    effective_risk = _assess_risk_level(
        payload.miss_distance_km, payload.collision_probability, payload.risk_level
    )

    # 4. Insert conjunction event record
    try:
        insert_data = payload.model_dump(mode="json")
        insert_data["risk_level"] = effective_risk

        insert_res = client.table("conjunction_events").insert(insert_data).execute()
        if not insert_res.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Conjunction event insertion succeeded but no record returned.",
            )
        return insert_res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record conjunction event: {_sanitize_error(exc)}",
        )
