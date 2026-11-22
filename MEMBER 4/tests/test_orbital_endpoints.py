"""Tests for Member 1 Orbital Engine adapter and FastAPI endpoints."""

import pytest
from app.adapters.member1_adapter import Member1Adapter
from app.routers.orbital import (
    get_orbital_metadata,
    get_orbital_satellites,
    get_orbital_trajectories,
    get_orbital_conjunctions,
    get_orbital_uncertainty,
    get_enriched_conjunctions,
)
from app.routers.coordination import get_coordination_status, get_all_conjunctions, get_scenario_conjunctions


def test_member1_adapter_availability():
    """Verify Member 1 dataset files are found on the filesystem."""
    assert Member1Adapter.is_available() is True


def test_member1_freshness_metadata():
    """Verify dataset freshness schema matches Member 1 output."""
    freshness = Member1Adapter.get_dataset_freshness()
    assert freshness.status == "online"
    assert freshness.data_freshness_status == "fresh"
    assert freshness.total_satellites == 200
    assert freshness.total_conjunctions == 40
    assert freshness.tle_sha256 is not None
    assert "2026" in freshness.conjunction_generated_at_utc


def test_member1_satellites_pagination():
    """Verify satellite catalogue loading and pagination."""
    res = Member1Adapter.get_satellites(limit=10, offset=0)
    assert res.total == 200
    assert res.count == 10
    assert len(res.items) == 10
    first = res.items[0]
    assert first.norad_id != ""
    assert first.name != ""
    assert first.line1.startswith("1 ")
    assert first.line2.startswith("2 ")
    assert first.tle_age_hours >= 0.0


def test_member1_conjunctions_raw():
    """Verify Member 1 raw conjunction screening schema."""
    res = Member1Adapter.get_conjunctions_raw()
    assert res.metadata.total_satellites == 200
    assert res.metadata.close_approaches == 40
    assert len(res.conjunctions) == 40
    first = res.conjunctions[0]
    assert first.norad_id_1 != ""
    assert first.norad_id_2 != ""
    assert first.miss_distance_km > 0.0
    assert "T" in first.tca_utc


def test_member1_uncertainty_raw():
    """Verify Member 1 uncertainty model schema."""
    res = Member1Adapter.get_uncertainty_raw()
    assert res.metadata.base_uncertainty_km == 0.1
    assert res.metadata.total_satellites == 200
    assert len(res.satellite_uncertainties) == 200
    first = res.satellite_uncertainties[0]
    assert first.norad_id != ""
    assert first.uncertainty_scale_km > 0.0


def test_member1_sampled_trajectories():
    """Verify downsampling of trajectories for 3D globe visualization."""
    res = Member1Adapter.get_sampled_trajectories(step=15, limit=5)
    assert res.metadata.sample_step == 15
    assert res.metadata.coordinate_frame == "GCRS"
    assert len(res.trajectories) == 5
    # Original is 4321 timestamps. Step=15 gives ceil(4321/15) = 289
    assert len(res.timestamps_utc) == 289
    first = res.trajectories[0]
    assert len(first.positions_km) == 289
    # Check that position vectors are 3D [x, y, z] in km
    assert len(first.positions_km[0]) == 3


def test_member1_enriched_with_member2():
    """Verify Member 1 conjunctions evaluated through Member 2 risk engine."""
    enriched = Member1Adapter.get_enriched_conjunctions_for_member2(limit=5)
    assert len(enriched) == 5
    for c in enriched:
        assert "collisionProbability" in c
        assert c["collisionProbability"] >= 0.0
        assert c["risk"] in ("critical", "high", "warning", "medium", "low", "monitor")
        assert c["isSynthetic"] is True
        assert "SYNTHETIC TEST OUTPUT" in c["syntheticWarning"]
        assert "manoeuvrePlan" in c


def test_orbital_endpoints():
    """Direct test of orbital router endpoints."""
    meta = get_orbital_metadata()
    assert meta.status == "online"

    sats = get_orbital_satellites(limit=5, offset=0)
    assert sats.count == 5

    trajs = get_orbital_trajectories(step=30, limit=2)
    assert len(trajs.trajectories) == 2

    conjs = get_orbital_conjunctions()
    assert len(conjs.conjunctions) == 40

    unc = get_orbital_uncertainty()
    assert len(unc.satellite_uncertainties) == 200

    enriched = get_enriched_conjunctions(limit=3)
    assert len(enriched) == 3


def test_coordination_status_includes_member1():
    """Verify coordination status reflects Member 1 integration."""
    status = get_coordination_status()
    assert status["member_1_engine"] == "connected"
    assert status["member_1_freshness"] is not None
    assert status["member_1_freshness"]["total_satellites"] == 200
    assert status["status"] == "online"


def test_coordination_conjunctions_includes_member1():
    """Verify coordination conjunctions include Member 1 events."""
    conjs = get_all_conjunctions()
    assert len(conjs) >= 42  # 40 from Member 1 + 2 demo scenarios
    m1_event = next((c for c in conjs if "C-M1-" in c["conjunction_id"]), None)
    assert m1_event is not None
    assert m1_event["isSynthetic"] is True
