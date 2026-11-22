"""Public entry point for Member 2. Input/output follows team guide Section 5.2."""

from config import DEFAULT_COMBINED_RADIUS_KM, PC_ACCEPTANCE_THRESHOLD
from anomaly_detection import detect_anomalies
from risk_engine import assess_conjunction
from coordinator import coordinate_and_plan


def run_member2(
    conjunction: dict,
    agent_a,
    agent_b,
    trajectory_evaluator,
    combined_radius_km: float = DEFAULT_COMBINED_RADIUS_KM,
    pc_threshold: float = PC_ACCEPTANCE_THRESHOLD,
) -> dict:
    risk = assess_conjunction(
        conjunction,
        combined_radius_km=combined_radius_km,
    )

    anomalies = detect_anomalies(conjunction)
    risk["anomaly_flag"] = anomalies["anomaly_flag"]
    if anomalies["flags"]:
        existing = risk["notes"]
        risk["notes"] = (existing + "; " if existing else "") + "; ".join(anomalies["flags"])

    plan = coordinate_and_plan(
        conjunction=conjunction,
        agent_a=agent_a,
        agent_b=agent_b,
        trajectory_evaluator=trajectory_evaluator,
        combined_radius_km=combined_radius_km,
        pc_threshold=pc_threshold,
    )

    return {
        "risk_assessment": risk,
        "manoeuvre_plan": plan,
        "anomaly_details": anomalies["flags"],
    }
