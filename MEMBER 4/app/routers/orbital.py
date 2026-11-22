"""Read-only FastAPI endpoints for Member 1 Orbital Engine.

Exposes Member 1 actual JSON schemas for:
- Dataset freshness and TLE metadata (/orbital/metadata)
- Orbital satellite catalogue (/orbital/satellites)
- Sampled GCRS trajectories for 3D globe visualization (/orbital/trajectories)
- Screened conjunction candidates (/orbital/conjunctions)
- TLE age-based uncertainty heuristic (/orbital/uncertainty)
- Enriched conjunction assessments connected to Member 2 (/orbital/enriched-conjunctions)
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.adapters.member1_adapter import (
    Member1Adapter,
    ConjunctionsResponse,
    DatasetFreshness,
    OrbitalSatellitesResponse,
    TrajectoriesResponse,
    UncertaintyResponse,
)

router = APIRouter(
    prefix="/orbital",
    tags=["Orbital Engine (Member 1)"],
)


@router.get(
    "/metadata",
    response_model=DatasetFreshness,
    summary="Get orbital dataset freshness and metadata",
    description="Returns generation timestamps, TLE SHA-256 hash, and dataset parameters from Member 1.",
)
def get_orbital_metadata() -> DatasetFreshness:
    return Member1Adapter.get_dataset_freshness()


@router.get(
    "/satellites",
    response_model=OrbitalSatellitesResponse,
    summary="List orbital satellites with TLE data",
    description="Returns the 200 satellites from Member 1's cleaned TLE catalogue with NORAD IDs, two-line element sets, and epoch ages.",
)
def get_orbital_satellites(
    search: Optional[str] = Query(None, description="Filter by satellite name or NORAD ID"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Offset index"),
) -> OrbitalSatellitesResponse:
    if not Member1Adapter.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member 1 orbital dataset files are not available.",
        )
    real_search = search if isinstance(search, str) else None
    real_limit = limit if isinstance(limit, int) else 50
    real_offset = offset if isinstance(offset, int) else 0
    return Member1Adapter.get_satellites(search=real_search, limit=real_limit, offset=real_offset)


@router.get(
    "/trajectories",
    response_model=TrajectoriesResponse,
    summary="Get sampled orbital trajectories in GCRS frame",
    description=(
        "Returns decimated 3D orbital trajectories for smooth rendering in CesiumJS. "
        "A step parameter of 15 reduces 4321 timestamps to 289 points per satellite."
    ),
)
def get_orbital_trajectories(
    step: int = Query(15, ge=1, le=120, description="Downsampling step across timestamps (e.g. 15 = every 15 mins)"),
    norad_id: Optional[List[str]] = Query(None, description="Optional NORAD ID(s) to filter"),
    limit: int = Query(20, ge=1, le=200, description="Number of satellites to return"),
    offset: int = Query(0, ge=0, description="Offset index"),
) -> TrajectoriesResponse:
    if not Member1Adapter.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member 1 trajectories dataset is not available.",
        )
    real_step = step if isinstance(step, int) else 15
    real_limit = limit if isinstance(limit, int) else 20
    real_offset = offset if isinstance(offset, int) else 0
    real_norad_ids = norad_id if isinstance(norad_id, (list, tuple, set)) else None
    return Member1Adapter.get_sampled_trajectories(
        step=real_step,
        norad_ids=real_norad_ids,
        limit=real_limit,
        offset=real_offset,
    )


@router.get(
    "/conjunctions",
    response_model=ConjunctionsResponse,
    summary="Get Member 1 screened conjunction candidate events",
    description="Returns the 40 close approach candidates from Member 1's continuous-run minimization screening.",
)
def get_orbital_conjunctions() -> ConjunctionsResponse:
    if not Member1Adapter.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member 1 conjunction dataset is not available.",
        )
    return Member1Adapter.get_conjunctions_raw()


@router.get(
    "/uncertainty",
    response_model=UncertaintyResponse,
    summary="Get Member 1 TLE-age uncertainty heuristic data",
    description="Returns linear TLE age-based uncertainty scales for all 200 satellites.",
)
def get_orbital_uncertainty() -> UncertaintyResponse:
    if not Member1Adapter.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member 1 uncertainty dataset is not available.",
        )
    return Member1Adapter.get_uncertainty_raw()


@router.get(
    "/enriched-conjunctions",
    summary="Get conjunctions evaluated through Member 2 risk engine",
    description=(
        "Integrates Member 1 close approaches with Member 2 collision probability (Pc) "
        "and risk classification. Manoeuvres remain labeled synthetic until flight repropagation is implemented."
    ),
)
def get_enriched_conjunctions(
    limit: int = Query(40, ge=1, le=100, description="Number of conjunction events to return")
):
    if not Member1Adapter.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member 1 conjunction dataset is not available.",
        )
    real_limit = limit if isinstance(limit, int) else 40
    return Member1Adapter.get_enriched_conjunctions_for_member2(limit=real_limit)
