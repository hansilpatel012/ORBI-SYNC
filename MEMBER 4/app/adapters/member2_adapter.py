"""Validated adapter connecting Member 4 FastAPI backend with Member 2 Risk & Coordination Engine.

Translates ORBI-SYNC Member 4 data models (satellites, orbital states, conjunctions)
into Member 2's encounter plane models, coordinates multi-agent avoidance plans,
and tags all synthetic results with transparent disclosures.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

# Ensure member2 and .venv site-packages are importable from either workspace root or MEMBER 4 directory
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MEMBER2_DIR = WORKSPACE_ROOT / "member2"
VENV_SITE_PACKAGES = WORKSPACE_ROOT / "MEMBER 4" / ".venv" / "Lib" / "site-packages"

if str(MEMBER2_DIR) not in sys.path and MEMBER2_DIR.exists():
    sys.path.insert(0, str(MEMBER2_DIR))

if str(VENV_SITE_PACKAGES) not in sys.path and VENV_SITE_PACKAGES.exists():
    sys.path.insert(0, str(VENV_SITE_PACKAGES))

# Import Member 2 intelligence engines
try:
    from risk_engine import assess_conjunction, calculate_pc_2d, classify_risk, sigma_from_uncertainty_scale
    from anomaly_detection import detect_anomalies
    from coordinator import coordinate_and_plan
    from agents import SatelliteAgent
    from demo_evaluator import synthetic_trajectory_evaluator
    from satellite_view_geometry import satellite_relative_geometry, risk_display_color
    from ai.report_generator import generate_ai_report
    MEMBER2_AVAILABLE = True
except ImportError as exc:  # pragma: no cover
    MEMBER2_AVAILABLE = False
    _IMPORT_ERROR = str(exc)

SYNTHETIC_EVALUATOR_WARNING = (
    "SYNTHETIC TEST OUTPUT: Trajectory evaluation uses a synthetic linear approximation "
    "(demo_evaluator.py). Certified collision avoidance maneuvers require Member 1's "
    "numerical propagation and secondary conjunction screening callable."
)

ISOTROPIC_GAUSSIAN_ASSUMPTION_NOTE = (
    "2D isotropic Gaussian encounter-plane model (noncentral chi-square df=2) under "
    "circular hard-body assumption. Uncertainty scale is team-calibrated to base sigma."
)


# ==============================================================================
# Pydantic Schemas for Validated Input/Output Contracts
# ==============================================================================

class ConjunctionAnalysisRequest(BaseModel):
    """Input payload for assessing conjunction risk and generating avoidance plans."""

    conjunction_id: Optional[str] = Field(
        default=None,
        description="Conjunction event ID (e.g. C-LEO-001). Generated automatically if omitted.",
    )
    satellite_1_id: str = Field(description="Primary satellite ID or UUID.")
    satellite_2_id: str = Field(description="Secondary satellite or debris ID or UUID.")
    tca: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Time of Closest Approach (TCA) in ISO 8601 UTC.",
    )
    miss_distance_km: float = Field(
        ge=0.0,
        description="Predicted miss distance in kilometers (>= 0.0).",
    )
    relative_speed_kms: float = Field(
        default=10.0,
        ge=0.0,
        description="Relative velocity at encounter in km/s (>= 0.0).",
    )
    tle_age_1_h: float = Field(
        default=12.0,
        ge=0.0,
        description="Age of Satellite 1 TLE in hours.",
    )
    tle_age_2_h: float = Field(
        default=12.0,
        ge=0.0,
        description="Age of Satellite 2 TLE in hours.",
    )
    uncertainty_scale: float = Field(
        default=1.0,
        gt=0.0,
        description="Dimensionless uncertainty scale factor (> 0.0).",
    )
    combined_radius_km: float = Field(
        default=0.01,
        gt=0.0,
        description="Combined hard-body radius in km (default 10 meters = 0.01 km).",
    )
    # Agent constraints for avoidance planning
    agent_1_can_manoeuvre: bool = Field(default=True, description="Whether Satellite 1 can manoeuvre.")
    agent_1_fuel_budget_ms: float = Field(default=1.5, ge=0.0, description="Satellite 1 delta-v budget in m/s.")
    agent_2_can_manoeuvre: bool = Field(default=False, description="Whether Satellite 2 can manoeuvre.")
    agent_2_fuel_budget_ms: float = Field(default=0.0, ge=0.0, description="Satellite 2 delta-v budget in m/s.")

    @field_validator("satellite_2_id")
    @classmethod
    def satellites_must_differ(cls, v: str, info) -> str:
        sat1 = info.data.get("satellite_1_id")
        if sat1 and v.strip() == sat1.strip():
            raise ValueError("satellite_1_id and satellite_2_id must be distinct assets.")
        return v


class RelativeGeometryRequest(BaseModel):
    """Input payload for satellite-relative encounter geometry calculation."""

    primary_position_km: List[float] = Field(description="[X, Y, Z] position of primary satellite in km.")
    primary_velocity_kms: List[float] = Field(description="[Vx, Vy, Vz] velocity of primary satellite in km/s.")
    secondary_position_km: List[float] = Field(description="[X, Y, Z] position of secondary satellite in km.")
    secondary_velocity_kms: List[float] = Field(description="[Vx, Vy, Vz] velocity of secondary satellite in km/s.")

    @field_validator(
        "primary_position_km",
        "primary_velocity_kms",
        "secondary_position_km",
        "secondary_velocity_kms",
    )
    @classmethod
    def validate_3d_vector(cls, v: List[float]) -> List[float]:
        if len(v) != 3:
            raise ValueError("Vector must contain exactly 3 coordinates [X, Y, Z].")
        return v


class RiskAssessmentResult(BaseModel):
    """Validated risk assessment output from Member 2."""

    conjunction_id: str
    pc: float = Field(ge=0.0, le=1.0, description="Collision probability Pc (0.0 to 1.0).")
    risk_level: str = Field(description="LOW, MEDIUM, HIGH, or CRITICAL.")
    anomaly_flag: bool
    notes: str
    anomaly_details: List[str] = Field(default_factory=list)
    is_synthetic: bool = True
    model_assumptions: str = ISOTROPIC_GAUSSIAN_ASSUMPTION_NOTE


class ManoeuvrePlanResult(BaseModel):
    """Validated collision avoidance plan output from Member 2."""

    plan_id: str
    conjunction_id: str
    status: str = Field(description="PROPOSED or REJECTED.")
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    total_dv_ms: float = Field(ge=0.0, description="Total delta-v required in m/s.")
    new_pc_after: Optional[float] = Field(default=None, description="Predicted post-manoeuvre collision probability.")
    fuel_cost_percent_of_budget: float = Field(ge=0.0, description="Fuel consumption as percentage of budget.")
    secondary_conjunctions: List[Any] = Field(default_factory=list)
    alternatives: List[Dict[str, Any]] = Field(default_factory=list)
    is_synthetic: bool = True
    synthetic_evaluator_warning: str = SYNTHETIC_EVALUATOR_WARNING


class RelativeGeometryResult(BaseModel):
    """Validated satellite-relative encounter geometry."""

    range_km: float
    azimuth_deg_along_track_to_cross_track: float
    elevation_deg_plane_to_radial: float
    closing_speed_kms: float
    motion_status: str
    display_color: str


class FullCoordinationReport(BaseModel):
    """Comprehensive intelligence output combining risk, manoeuvre plan, and situation briefing."""

    conjunction_id: str
    timestamp: str
    risk_assessment: RiskAssessmentResult
    manoeuvre_plan: ManoeuvrePlanResult
    relative_geometry: Optional[RelativeGeometryResult] = None
    briefing_report: str
    report_mode: str
    evaluator_mode: str = "SYNTHETIC_DEMO"
    missing_dependencies: List[str] = Field(
        default_factory=lambda: [
            "Member 1 Trajectory Evaluator: callable(conjunction: dict, actions: list[dict]) -> dict",
            "Member 1 Numerical Orbit Propagator: SGP4/numerical ephemeris replacing circular two-body model",
            "Member 1 Encounter Covariance Matrix: 3x3/6x6 error ellipsoids replacing dimensionless uncertainty_scale",
            "Member 1 Post-Manoeuvre Secondary Screening: full catalog screening for secondary collision risks",
        ]
    )


# ==============================================================================
# Adapter Engine Functions
# ==============================================================================

class Member2Adapter:
    """Adapter bridging Member 4 FastAPI endpoints with Member 2 intelligence engine."""

    @staticmethod
    def is_available() -> bool:
        return MEMBER2_AVAILABLE

    @staticmethod
    def run_analysis(
        request: ConjunctionAnalysisRequest,
        trajectory_evaluator: Optional[Any] = None,
    ) -> FullCoordinationReport:
        """Executes Member 2 risk assessment and manoeuvre coordination with validated inputs."""
        if not MEMBER2_AVAILABLE:
            raise RuntimeError("Member 2 intelligence engine is not available.")

        cid = request.conjunction_id or f"C-{uuid4().hex[:8].upper()}"
        evaluator = trajectory_evaluator or synthetic_trajectory_evaluator
        evaluator_mode = "MEMBER_1_INTEGRATED" if trajectory_evaluator else "SYNTHETIC_DEMO"

        conjunction_dict = {
            "conjunction_id": cid,
            "object_a": request.satellite_1_id,
            "object_b": request.satellite_2_id,
            "tca": request.tca.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "miss_distance_km": request.miss_distance_km,
            "relative_speed_kms": request.relative_speed_kms,
            "data_quality": {
                "tle_age_a_h": request.tle_age_1_h,
                "tle_age_b_h": request.tle_age_2_h,
                "uncertainty_scale": request.uncertainty_scale,
            },
        }

        # 1. Anomaly detection
        anomalies = detect_anomalies(conjunction_dict)

        # 2. Risk scoring (Pc via 2D Gaussian)
        risk = assess_conjunction(
            conjunction_dict,
            combined_radius_km=request.combined_radius_km,
        )
        risk["anomaly_flag"] = anomalies["anomaly_flag"]
        if anomalies["flags"]:
            existing = risk["notes"]
            risk["notes"] = (existing + "; " if existing else "") + "; ".join(anomalies["flags"])

        # 3. Agent construction
        agent_a = SatelliteAgent(
            object_id=request.satellite_1_id,
            can_manoeuvre=request.agent_1_can_manoeuvre,
            fuel_budget_ms=request.agent_1_fuel_budget_ms,
        )
        agent_b = SatelliteAgent(
            object_id=request.satellite_2_id,
            can_manoeuvre=request.agent_2_can_manoeuvre,
            fuel_budget_ms=request.agent_2_fuel_budget_ms,
        )

        # 4. Multi-agent coordination and avoidance planning
        plan = coordinate_and_plan(
            conjunction=conjunction_dict,
            agent_a=agent_a,
            agent_b=agent_b,
            trajectory_evaluator=evaluator,
            combined_radius_km=request.combined_radius_km,
            pc_threshold=1e-4,
        )

        # 5. Briefing report generation
        combined_payload = {
            "risk_assessment": risk,
            "manoeuvre_plan": plan,
            "anomaly_details": anomalies["flags"],
            "conjunction_input": conjunction_dict,
            "evaluation_mode": "synthetic_demo" if evaluator_mode == "SYNTHETIC_DEMO" else "operational",
        }
        report_data = generate_ai_report(combined_payload)

        # 6. Wrap in validated Pydantic models
        risk_result = RiskAssessmentResult(
            conjunction_id=cid,
            pc=risk["pc"],
            risk_level=risk["risk_level"],
            anomaly_flag=risk["anomaly_flag"],
            notes=risk["notes"],
            anomaly_details=anomalies["flags"],
            is_synthetic=True,
            model_assumptions=ISOTROPIC_GAUSSIAN_ASSUMPTION_NOTE,
        )

        plan_result = ManoeuvrePlanResult(
            plan_id=plan["plan_id"],
            conjunction_id=cid,
            status=plan["status"],
            actions=plan["actions"],
            total_dv_ms=plan["total_dv_ms"],
            new_pc_after=plan.get("new_pc_after"),
            fuel_cost_percent_of_budget=plan["fuel_cost_percent_of_budget"],
            secondary_conjunctions=plan["secondary_conjunctions"],
            alternatives=plan.get("alternatives", []),
            is_synthetic=True,
            synthetic_evaluator_warning=SYNTHETIC_EVALUATOR_WARNING,
        )

        return FullCoordinationReport(
            conjunction_id=cid,
            timestamp=datetime.now(timezone.utc).isoformat(),
            risk_assessment=risk_result,
            manoeuvre_plan=plan_result,
            relative_geometry=None,
            briefing_report=report_data.get("report", ""),
            report_mode=report_data.get("mode", "local_fallback"),
            evaluator_mode=evaluator_mode,
        )

    @staticmethod
    def calculate_relative_geometry(
        request: RelativeGeometryRequest,
        risk_level: str = "MEDIUM",
    ) -> RelativeGeometryResult:
        """Calculates encounter-plane RTN relative geometry."""
        if not MEMBER2_AVAILABLE:
            raise RuntimeError("Member 2 intelligence engine is not available.")

        geom = satellite_relative_geometry(
            satellite_position_km=request.primary_position_km,
            satellite_velocity_kms=request.primary_velocity_kms,
            target_position_km=request.secondary_position_km,
            target_velocity_kms=request.secondary_velocity_kms,
        )

        color = risk_display_color(risk_level)

        return RelativeGeometryResult(
            range_km=geom["range_km"],
            azimuth_deg_along_track_to_cross_track=geom["azimuth_deg_from_along_track_toward_cross_track"],
            elevation_deg_plane_to_radial=geom["elevation_deg_from_orbital_plane_toward_radial"],
            closing_speed_kms=geom["closing_speed_kms"],
            motion_status=geom["motion_status"],
            display_color=color,
        )
