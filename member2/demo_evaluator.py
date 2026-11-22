"""SYNTHETIC TEST-ONLY evaluator.

This is not orbital mechanics. It exists only so the Member 2 software flow
can be run before Member 1 supplies the real modified-trajectory evaluator.
Never use its outputs as real manoeuvre predictions or show them as validated
orbital results to judges.
"""


def synthetic_trajectory_evaluator(conjunction: dict, actions: list[dict]) -> dict:
    if not actions:
        return {
            "miss_distance_km": float(conjunction["miss_distance_km"]),
            "secondary_conjunctions": [],
        }

    # Deterministic synthetic mapping solely to exercise code paths.
    # Replace this entire function with Member 1's propagation/re-screening.
    total_dv = sum(action["dv_ms"] for action in actions)
    synthetic_gain_km = 2.0 * total_dv
    new_distance = float(conjunction["miss_distance_km"]) + synthetic_gain_km

    return {
        "miss_distance_km": new_distance,
        "secondary_conjunctions": [],
    }
