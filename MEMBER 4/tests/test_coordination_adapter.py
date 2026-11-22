"""Tests for Member 2 Adapter and Coordination API Endpoints in Member 4."""

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from app.adapters.member2_adapter import (
    ConjunctionAnalysisRequest,
    Member2Adapter,
    RelativeGeometryRequest,
    SYNTHETIC_EVALUATOR_WARNING,
)
from app.routers.coordination import (
    assess_risk,
    calculate_relative_geometry,
    full_analysis,
    get_coordination_status,
    get_scenario_conjunctions,
    plan_manoeuvre,
)


def test_member2_engine_availability():
    """Verifies that Member 2 engine modules are detected and imported."""
    assert Member2Adapter.is_available() is True


def test_coordination_status_endpoint():
    """Verifies GET /coordination/status returns engine info and enumerates missing Member 1 dependencies."""
    status_data = get_coordination_status()
    assert status_data["status"] == "online"
    assert status_data["member_2_engine"] == "connected"
    assert status_data["evaluator_mode"] == "SYNTHETIC_DEMO"
    assert status_data["is_synthetic"] is True
    assert len(status_data["supported_features"]) >= 5
    assert len(status_data["missing_member_1_dependencies"]) == 4
    assert any("Member 1 Trajectory Evaluator" in dep for dep in status_data["missing_member_1_dependencies"])


def test_assess_risk_direct_adapter():
    """Verifies 2D encounter-plane Pc and anomaly detection via Member2Adapter."""
    req = ConjunctionAnalysisRequest(
        conjunction_id="C-TEST-LEO-01",
        satellite_1_id="sat-alpha",
        satellite_2_id="debris-beta",
        tca=datetime.now(timezone.utc),
        miss_distance_km=0.35,
        relative_speed_kms=10.2,
        tle_age_1_h=12.0,
        tle_age_2_h=96.0,  # >72 hours triggers stale TLE anomaly
        uncertainty_scale=1.5,
    )
    report = Member2Adapter.run_analysis(req)
    risk = report.risk_assessment

    assert risk.conjunction_id == "C-TEST-LEO-01"
    assert 0.0 <= risk.pc <= 1.0
    assert risk.risk_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert risk.anomaly_flag is True
    assert any("stale" in str(note).lower() for note in risk.anomaly_details)
    assert risk.is_synthetic is True


def test_plan_manoeuvre_direct_adapter():
    """Verifies multi-agent collision avoidance planning with alternatives."""
    req = ConjunctionAnalysisRequest(
        conjunction_id="C-TEST-LEO-02",
        satellite_1_id="sat-alpha",
        satellite_2_id="debris-beta",
        tca=datetime.now(timezone.utc),
        miss_distance_km=0.25,
        relative_speed_kms=9.5,
        agent_1_can_manoeuvre=True,
        agent_1_fuel_budget_ms=2.0,
        agent_2_can_manoeuvre=False,
        agent_2_fuel_budget_ms=0.0,
    )
    report = Member2Adapter.run_analysis(req)
    plan = report.manoeuvre_plan

    assert plan.conjunction_id == "C-TEST-LEO-02"
    assert plan.status in ("PROPOSED", "REJECTED")
    assert plan.total_dv_ms >= 0.0
    assert plan.is_synthetic is True
    assert plan.synthetic_evaluator_warning == SYNTHETIC_EVALUATOR_WARNING
    assert isinstance(plan.actions, list)


def test_calculate_relative_geometry_direct_adapter():
    """Verifies RTN relative encounter geometry calculation."""
    req = RelativeGeometryRequest(
        primary_position_km=[7000.0, 0.0, 0.0],
        primary_velocity_kms=[0.0, 7.5, 0.0],
        secondary_position_km=[7000.0, 10.0, 0.0],
        secondary_velocity_kms=[0.0, 7.5, 0.0],
    )
    result = Member2Adapter.calculate_relative_geometry(req, risk_level="HIGH")
    assert result.range_km == pytest.approx(10.0, rel=1e-3)
    assert result.azimuth_deg_along_track_to_cross_track == pytest.approx(0.0, abs=1e-2)
    assert result.display_color == "orange"


def test_scenario_conjunctions_for_frontend():
    """Verifies that scenario conjunctions return enriched Member 2 calculations for frontend."""
    results = get_scenario_conjunctions()
    assert len(results) == 2
    for item in results:
        assert "id" in item
        assert "conjunction_id" in item
        assert "collisionProbability" in item
        assert 0.0 <= item["collisionProbability"] <= 1.0
        assert item["risk"] in ("critical", "high", "medium", "low")
        assert item["isSynthetic"] is True
        assert "manoeuvrePlan" in item
        assert "briefingReport" in item


def test_validation_rejects_identical_satellites():
    """Verifies request validator rejects identical satellite IDs."""
    with pytest.raises(Exception):
        ConjunctionAnalysisRequest(
            satellite_1_id="same-asset-id",
            satellite_2_id="same-asset-id",
            miss_distance_km=0.5,
        )


def test_validation_rejects_negative_miss_distance():
    """Verifies request validator rejects negative miss distance."""
    with pytest.raises(Exception):
        ConjunctionAnalysisRequest(
            satellite_1_id="sat-1",
            satellite_2_id="sat-2",
            miss_distance_km=-1.0,
        )
