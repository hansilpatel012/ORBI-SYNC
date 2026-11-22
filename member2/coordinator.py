"""Multi-agent coordination and plan serialization."""

from __future__ import annotations
from uuid import uuid4
from config import MAX_ALTERNATIVES
from planner import generate_plan_candidates


def coordinate_and_plan(
    conjunction: dict,
    agent_a,
    agent_b,
    trajectory_evaluator,
    combined_radius_km: float,
    pc_threshold: float,
) -> dict:
    candidates = generate_plan_candidates(
        conjunction=conjunction,
        agent_a=agent_a,
        agent_b=agent_b,
        trajectory_evaluator=trajectory_evaluator,
        combined_radius_km=combined_radius_km,
        pc_threshold=pc_threshold,
    )

    if not candidates:
        return {
            "plan_id": f"P-{uuid4().hex[:8].upper()}",
            "conjunction_id": conjunction["conjunction_id"],
            "actions": [],
            "total_dv_ms": 0.0,
            "new_pc_after": None,
            "secondary_conjunctions": [],
            "fuel_cost_percent_of_budget": 0.0,
            "alternatives": [],
            "status": "REJECTED",
        }

    selected = candidates[0]
    alternatives = candidates[1:MAX_ALTERNATIVES + 1]

    return {
        "plan_id": f"P-{uuid4().hex[:8].upper()}",
        "conjunction_id": conjunction["conjunction_id"],
        "actions": selected["actions"],
        "total_dv_ms": selected["total_dv_ms"],
        "new_pc_after": selected["new_pc_after"],
        "secondary_conjunctions": selected["secondary_conjunctions"],
        "fuel_cost_percent_of_budget": selected["fuel_cost_percent_of_budget"],
        "alternatives": alternatives,
        "status": "PROPOSED",
    }
