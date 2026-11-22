"""Run the Member 2 pipeline with synthetic demo data.

This verifies software wiring only. The manoeuvre evaluator is synthetic;
replace it with Member 1's real propagation and secondary-screening callback.
"""

import json
from agents import SatelliteAgent
from demo_evaluator import synthetic_trajectory_evaluator
from member2_engine import run_member2
from sample_data import SAMPLE_CONJUNCTION


if __name__ == "__main__":
    satellite_a = SatelliteAgent(
        object_id="SAT-A",
        can_manoeuvre=True,
        fuel_budget_ms=1.5,
        mission_rules={"max_dv_ms": 0.5, "max_orbit_change_km": 5.0},
    )
    debris_b = SatelliteAgent(
        object_id="DEBRIS-B",
        can_manoeuvre=False,
        fuel_budget_ms=0.0,
    )

    result = run_member2(
        conjunction=SAMPLE_CONJUNCTION,
        agent_a=satellite_a,
        agent_b=debris_b,
        trajectory_evaluator=synthetic_trajectory_evaluator,
    )
    print(json.dumps(result, indent=2))
    print("\nWARNING: manoeuvre results above are SYNTHETIC TEST OUTPUTS.")
