"""Coordination & Conjunction Intelligence API Router.

Integrates Member 2's collision risk engine and multi-agent coordination planner
with Member 4's central FastAPI backend.
"""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.adapters.member2_adapter import (
    ConjunctionAnalysisRequest,
    FullCoordinationReport,
    ManoeuvrePlanResult,
    Member2Adapter,
    RelativeGeometryRequest,
    RelativeGeometryResult,
    RiskAssessmentResult,
    SYNTHETIC_EVALUATOR_WARNING,
)
from app.adapters.member1_adapter import Member1Adapter
from app.auth import AuthUser, require_operator

router = APIRouter(prefix="/coordination", tags=["Coordination & Intelligence (Member 2)"])


@router.get(
    "/status",
    summary="Check Coordination Engine & Member 2 Integration Status",
    response_model=Dict[str, Any],
)
def get_coordination_status() -> Dict[str, Any]:
    """Returns the operational status of Member 2 intelligence engine and its dependency contracts."""
    m2_available = Member2Adapter.is_available()
    m1_available = Member1Adapter.is_available()
    freshness = Member1Adapter.get_dataset_freshness() if m1_available else None
    return {
        "status": "online" if m2_available and m1_available else ("partial" if m2_available else "degraded"),
        "member_2_engine": "connected" if m2_available else "missing",
        "member_1_engine": "connected" if m1_available else "missing",
        "member_1_freshness": freshness.model_dump() if freshness else None,
        "evaluator_mode": "SYNTHETIC_DEMO",
        "evaluator_warning": SYNTHETIC_EVALUATOR_WARNING,
        "is_synthetic": True,
        "supported_features": [
            "Member 1 SGP4 High-Precision Propagated Ephemerides (GCRS frame, 200 satellites)",
            "Member 1 Continuous-Run Local Minima Conjunction Screening (40 candidate events)",
            "Member 1 Linear TLE-Age Uncertainty Scaling (RSS heuristic model)",
            "2D Isotropic Gaussian Encounter-Plane Pc (scipy.stats.ncx2)",
            "Rule-based Anomaly Detection (stale TLEs, negative distances, abnormal speeds)",
            "Multi-Agent Manoeuvre Coordination (A-moves, B-moves, joint actions)",
            "Candidate Generation (burn lead hours, delta-v steps, along-track directions)",
            "Satellite RTN Relative Geometry (range, azimuth, elevation, closing speed)",
            "Situational Briefing Generator (local template fallback without external API key)",
        ],
        "missing_member_1_dependencies": [
            "Member 1 Trajectory Evaluator: callable(conjunction: dict, actions: list[dict]) -> dict",
            "Member 1 Numerical Orbit Propagator: SGP4/numerical ephemeris replacing circular two-body model",
            "Member 1 Encounter Covariance Matrix: 3x3/6x6 error ellipsoids replacing dimensionless uncertainty_scale",
            "Member 1 Post-Manoeuvre Secondary Screening: full catalog screening for secondary collision risks",
        ],
    }


@router.post(
    "/assess-risk",
    summary="Assess Conjunction Risk & Compute Pc (Public / Viewer)",
    response_model=RiskAssessmentResult,
)
def assess_risk(request: ConjunctionAnalysisRequest) -> RiskAssessmentResult:
    """Computes collision probability Pc and checks data anomalies using Member 2 risk engine."""
    if not Member2Adapter.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member 2 intelligence engine is unavailable.",
        )
    try:
        report = Member2Adapter.run_analysis(request)
        return report.risk_assessment
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Risk assessment failed: {str(exc)}",
        )


@router.post(
    "/plan-manoeuvre",
    summary="Generate Coordinated Avoidance Plan (Operator or Admin required)",
    response_model=ManoeuvrePlanResult,
)
def plan_manoeuvre(
    request: ConjunctionAnalysisRequest,
    current_user: AuthUser = Depends(require_operator),
) -> ManoeuvrePlanResult:
    """Generates multi-agent collision avoidance plans with candidate burns and alternatives."""
    if not Member2Adapter.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member 2 intelligence engine is unavailable.",
        )
    try:
        report = Member2Adapter.run_analysis(request)
        return report.manoeuvre_plan
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Avoidance planning failed: {str(exc)}",
        )


@router.post(
    "/relative-geometry",
    summary="Calculate Satellite-Relative Encounter Geometry (RTN Frame)",
    response_model=RelativeGeometryResult,
)
def calculate_relative_geometry(
    request: RelativeGeometryRequest,
    risk_level: str = "MEDIUM",
) -> RelativeGeometryResult:
    """Calculates radial, along-track, cross-track (RTN) encounter geometry."""
    if not Member2Adapter.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member 2 intelligence engine is unavailable.",
        )
    try:
        return Member2Adapter.calculate_relative_geometry(request, risk_level=risk_level)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Relative geometry calculation failed: {str(exc)}",
        )


@router.post(
    "/full-analysis",
    summary="Execute Full Conjunction Intelligence & Briefing Pipeline",
    response_model=FullCoordinationReport,
)
def full_analysis(request: ConjunctionAnalysisRequest) -> FullCoordinationReport:
    """Runs complete Member 2 pipeline: anomaly detection, Pc computation, avoidance planning, and situational briefing."""
    if not Member2Adapter.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member 2 intelligence engine is unavailable.",
        )
    try:
        return Member2Adapter.run_analysis(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Full coordination analysis failed: {str(exc)}",
        )


@router.get(
    "/conjunctions",
    summary="Get Analyzed Conjunctions (Member 1 Screened + Demo Scenarios)",
    response_model=List[Dict[str, Any]],
)
def get_all_conjunctions(
    include_member1: bool = Query(True, description="Include Member 1 screened conjunctions"),
    limit: int = Query(40, ge=1, le=100, description="Max Member 1 conjunctions"),
) -> List[Dict[str, Any]]:
    """Returns all conjunctions enriched by Member 2, merging Member 1 screened events with demo scenarios."""
    real_inc = include_member1 if isinstance(include_member1, bool) else True
    real_lim = limit if isinstance(limit, int) else 40
    results = []
    if real_inc and Member1Adapter.is_available():
        try:
            m1_enriched = Member1Adapter.get_enriched_conjunctions_for_member2(limit=real_lim)
            results.extend(m1_enriched)
        except Exception:
            pass
    results.extend(get_scenario_conjunctions())
    return results


@router.get(
    "/scenario-conjunctions",
    summary="Get Analyzed Demonstration Scenario Conjunctions (for Frontend)",
    response_model=List[Dict[str, Any]],
)
def get_scenario_conjunctions() -> List[Dict[str, Any]]:
    """Returns pre-evaluated scenario conjunctions enriched with Member 2 Pc, risk levels, and maneuver options."""
    if not Member2Adapter.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Member 2 intelligence engine is unavailable.",
        )

    results = []

    # Standard scenario encounters corresponding to the frontend simulation
    scenarios = [
        {
            "id": "cnj-orbi-sat-1-sim-deb-0417",
            "conjunction_id": "C-DEMO-LEO-01",
            "satellite_1_id": "orbi-sat-1",
            "satellite_2_id": "sim-deb-0417",
            "miss_distance_km": 0.35,
            "relative_speed_kms": 10.2,
            "tle_age_1_h": 12.0,
            "tle_age_2_h": 24.0,
            "uncertainty_scale": 1.5,
            "tca": "2026-11-25T14:30:00Z",
            "agent_1_can_manoeuvre": True,
            "agent_1_fuel_budget_ms": 1.5,
            "agent_2_can_manoeuvre": False,
            "agent_2_fuel_budget_ms": 0.0,
        },
        {
            "id": "cnj-orbi-sat-2-sim-rb-2207",
            "conjunction_id": "C-DEMO-LEO-02",
            "satellite_1_id": "orbi-sat-2",
            "satellite_2_id": "sim-rb-2207",
            "miss_distance_km": 3.1,
            "relative_speed_kms": 7.8,
            "tle_age_1_h": 8.0,
            "tle_age_2_h": 18.0,
            "uncertainty_scale": 1.2,
            "tca": "2026-11-26T08:15:00Z",
            "agent_1_can_manoeuvre": True,
            "agent_1_fuel_budget_ms": 2.0,
            "agent_2_can_manoeuvre": False,
            "agent_2_fuel_budget_ms": 0.0,
        },
    ]

    for sc in scenarios:
        req = ConjunctionAnalysisRequest(
            conjunction_id=sc["conjunction_id"],
            satellite_1_id=sc["satellite_1_id"],
            satellite_2_id=sc["satellite_2_id"],
            miss_distance_km=sc["miss_distance_km"],
            relative_speed_kms=sc["relative_speed_kms"],
            tle_age_1_h=sc["tle_age_1_h"],
            tle_age_2_h=sc["tle_age_2_h"],
            uncertainty_scale=sc["uncertainty_scale"],
            agent_1_can_manoeuvre=sc["agent_1_can_manoeuvre"],
            agent_1_fuel_budget_ms=sc["agent_1_fuel_budget_ms"],
            agent_2_can_manoeuvre=sc["agent_2_can_manoeuvre"],
            agent_2_fuel_budget_ms=sc["agent_2_fuel_budget_ms"],
        )
        report = Member2Adapter.run_analysis(req)
        results.append({
            "id": sc["id"],
            "conjunction_id": sc["conjunction_id"],
            "objectA": sc["satellite_1_id"],
            "objectB": sc["satellite_2_id"],
            "missDistanceKm": sc["miss_distance_km"],
            "relativeVelocityKmS": sc["relative_speed_kms"],
            "tcaIso": sc["tca"],
            "collisionProbability": report.risk_assessment.pc,
            "risk": report.risk_assessment.risk_level.lower(),
            "risk_level": report.risk_assessment.risk_level,
            "anomalyFlag": report.risk_assessment.anomaly_flag,
            "notes": report.risk_assessment.notes,
            "manoeuvrePlan": report.manoeuvre_plan.model_dump(),
            "briefingReport": report.briefing_report,
            "isSynthetic": True,
            "source": "FastAPI + Member 2 Intelligence Engine (Synthetic Evaluator)",
            "syntheticWarning": SYNTHETIC_EVALUATOR_WARNING,
        })

    return results
