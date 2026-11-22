"""Candidate generation and evaluation.

Physical trajectory evaluation is deliberately injected as a callback. Member
1 must provide the evaluator that applies a candidate impulse, propagates the
modified trajectory, recomputes TCA/miss distance, and re-screens secondary
conjunctions. This module does NOT invent a km-per-m/s effectiveness factor.
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from itertools import product

from config import (
    BURN_LEAD_HOURS,
    CANDIDATE_DIRECTIONS,
    CANDIDATE_DV_MS,
    DEFAULT_COMBINED_RADIUS_KM,
    PC_ACCEPTANCE_THRESHOLD,
)
from risk_engine import calculate_pc_2d, sigma_from_uncertainty_scale


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamps must include timezone; guide requires UTC ISO 8601.")
    return parsed.astimezone(timezone.utc)


def build_candidate_actions(conjunction: dict, agent) -> list[dict]:
    if not agent.can_manoeuvre:
        return []

    tca = parse_utc(conjunction["tca"])
    actions = []
    for lead_hours, dv, direction in product(
        BURN_LEAD_HOURS, CANDIDATE_DV_MS, CANDIDATE_DIRECTIONS
    ):
        burn_time = tca - timedelta(hours=lead_hours)
        if agent.can_accept_manoeuvre(dv_ms=dv):
            actions.append({
                "object_id": agent.object_id,
                "burn_time": burn_time.isoformat().replace("+00:00", "Z"),
                "direction": direction,
                "dv_ms": float(dv),
            })
    return actions


def evaluate_action_set(
    conjunction: dict,
    actions: list[dict],
    trajectory_evaluator,
    sigma_km: float,
    combined_radius_km: float = DEFAULT_COMBINED_RADIUS_KM,
) -> dict:
    """Evaluate complete action set using Member 1's physical evaluator.

    Callback contract:
      trajectory_evaluator(conjunction, actions) -> {
        "miss_distance_km": float,
        "secondary_conjunctions": list
      }
    """
    outcome = trajectory_evaluator(conjunction, actions)
    new_distance = float(outcome["miss_distance_km"])
    pc = calculate_pc_2d(new_distance, combined_radius_km, sigma_km)
    secondary = outcome.get("secondary_conjunctions", [])
    return {
        "new_miss_distance_km": new_distance,
        "new_pc_after": pc,
        "secondary_conjunctions": secondary,
    }


def generate_plan_candidates(
    conjunction: dict,
    agent_a,
    agent_b,
    trajectory_evaluator,
    combined_radius_km: float = DEFAULT_COMBINED_RADIUS_KM,
    pc_threshold: float = PC_ACCEPTANCE_THRESHOLD,
) -> list[dict]:
    """Enumerate A-only, B-only and joint candidate plans."""
    dq = conjunction["data_quality"]
    sigma = sigma_from_uncertainty_scale(dq["uncertainty_scale"])

    actions_a = build_candidate_actions(conjunction, agent_a)
    actions_b = build_candidate_actions(conjunction, agent_b)

    action_sets = []
    action_sets.extend([[a] for a in actions_a])
    action_sets.extend([[b] for b in actions_b])
    action_sets.extend([[a, b] for a in actions_a for b in actions_b])

    feasible = []
    for actions in action_sets:
        # Each action is checked against its own agent's budget and rules.
        agent_map = {agent_a.object_id: agent_a, agent_b.object_id: agent_b}
        if any(
            action["object_id"] not in agent_map
            or not agent_map[action["object_id"]].can_accept_manoeuvre(action["dv_ms"])
            for action in actions
        ):
            continue

        try:
            result = evaluate_action_set(
                conjunction, actions, trajectory_evaluator,
                sigma, combined_radius_km
            )
        except (ValueError, KeyError, NotImplementedError):
            # Invalid/unavailable propagation means this candidate cannot be
            # certified safe; do not silently treat it as successful.
            continue

        if result["new_pc_after"] >= pc_threshold:
            continue
        if result["secondary_conjunctions"]:
            continue

        total_dv = sum(action["dv_ms"] for action in actions)
        budget_percent = sum(
            agent_map[action["object_id"]].fuel_cost_percent(action["dv_ms"])
            for action in actions
        )
        strategy = (
            "BOTH_MOVE" if len(actions) == 2
            else ("A_MOVES" if actions[0]["object_id"] == agent_a.object_id else "B_MOVES")
        )

        feasible.append({
            "strategy": strategy,
            "actions": actions,
            "total_dv_ms": total_dv,
            "new_miss_distance_km": result["new_miss_distance_km"],
            "new_pc_after": result["new_pc_after"],
            "secondary_conjunctions": result["secondary_conjunctions"],
            "fuel_cost_percent_of_budget": budget_percent,
            "status": "PROPOSED",
        })

    # Lowest total delta-v first, then lowest Pc.
    feasible.sort(key=lambda item: (item["total_dv_ms"], item["new_pc_after"]))
    return feasible
