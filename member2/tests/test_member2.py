import pytest

from risk_engine import calculate_pc_2d, classify_risk, assess_conjunction
from anomaly_detection import detect_anomalies
from agents import SatelliteAgent
from demo_evaluator import synthetic_trajectory_evaluator
from member2_engine import run_member2
from sample_data import SAMPLE_CONJUNCTION


def test_pc_is_probability():
    pc = calculate_pc_2d(0.2, 0.01, 0.1)
    assert 0.0 <= pc <= 1.0


def test_closer_encounter_has_higher_pc():
    near = calculate_pc_2d(0.1, 0.01, 0.1)
    far = calculate_pc_2d(1.0, 0.01, 0.1)
    assert near > far


def test_pc_rejects_invalid_sigma():
    with pytest.raises(ValueError):
        calculate_pc_2d(0.2, 0.01, 0.0)


def test_risk_labels():
    assert classify_risk(1e-7) == "LOW"
    assert classify_risk(2e-6) == "MEDIUM"
    assert classify_risk(2e-5) == "HIGH"
    assert classify_risk(2e-4) == "HIGH"
    assert classify_risk(2e-3) == "CRITICAL"


def test_stale_tle_flag():
    event = {
        **SAMPLE_CONJUNCTION,
        "data_quality": {
            "tle_age_a_h": 10,
            "tle_age_b_h": 100,
            "uncertainty_scale": 1.0,
        },
    }
    result = detect_anomalies(event)
    assert result["anomaly_flag"] is True


def test_agent_fuel_limit():
    agent = SatelliteAgent("SAT-A", True, 0.1)
    assert agent.can_accept_manoeuvre(0.05)
    assert not agent.can_accept_manoeuvre(0.2)


def test_debris_cannot_manoeuvre():
    debris = SatelliteAgent("DEBRIS", False, 0.0)
    assert not debris.can_accept_manoeuvre(0.01)


def test_end_to_end_demo_returns_guide_keys():
    a = SatelliteAgent("SAT-A", True, 1.5)
    b = SatelliteAgent("DEBRIS-B", False, 0.0)
    output = run_member2(
        SAMPLE_CONJUNCTION, a, b, synthetic_trajectory_evaluator
    )
    risk = output["risk_assessment"]
    plan = output["manoeuvre_plan"]

    assert set(risk) == {
        "conjunction_id", "pc", "risk_level", "anomaly_flag", "notes"
    }
    assert set(plan) == {
        "plan_id", "conjunction_id", "actions", "total_dv_ms",
        "new_pc_after", "secondary_conjunctions",
        "fuel_cost_percent_of_budget", "alternatives", "status"
    }
