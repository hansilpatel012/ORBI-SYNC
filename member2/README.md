# ORBI-SYNC — Member 2 Intelligence & Coordination

This folder implements Member 2's portion of ORBI-SYNC using the shared
interfaces in ORBI-SYNC Team Guide, Sections 5.2 and 6.

## What is implemented

1. Risk score (`Pc`) using the guide-requested simple 2D Gaussian encounter-
   plane model under an explicitly stated isotropic covariance assumption.
2. Rule-based anomaly flags (stale TLE, missing/invalid fields).
3. Satellite agents with manoeuvre/fuel/mission constraints.
4. Candidate burn times and delta-v values.
5. Coordinator compares A-only, B-only and joint actions.
6. Lowest-delta-v feasible plans are returned with alternatives.
7. Exact top-level Risk Assessment and Manoeuvre Plan field names from
   Section 5.2.

## Critical scientific limitations

- The conjunction JSON in Section 5.2 does not contain full encounter-plane
  covariance, hard-body radii, or object-specific physical radii.
- `BASE_SIGMA_KM` and `DEFAULT_COMBINED_RADIUS_KM` in `config.py` are
  illustrative demo assumptions. Replace them with agreed, documented values.
- The current 2D Pc implementation assumes isotropic encounter-plane
  uncertainty: covariance = sigma^2 times identity. It is a simple prototype
  model, not a complete operational NASA CARA implementation.
- `uncertainty_scale` is dimensionless. Multiplying it by a base sigma is a
  team calibration assumption, not a value supplied by the TLE itself.
- The synthetic evaluator in `demo_evaluator.py` is ONLY for testing software
  wiring. It is not orbital mechanics and must not be presented as a real
  manoeuvre simulation.
- Before using a candidate as a scientific result, Member 1 must supply a
  trajectory evaluator that applies the impulse, propagates the changed
  trajectory, recomputes TCA/miss distance, and re-screens secondary
  conjunctions. If that evaluator is missing, no manoeuvre can be certified.

## Setup (Windows PowerShell)

```powershell
cd orbi_sync_member2
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the synthetic software demo

```powershell
python main.py
```

The output includes a warning that the manoeuvre results are synthetic.

## Run tests

```powershell
python -m pytest -v
```

## Integration with Member 1

Member 1 must provide a callable with this interface:

```python
def trajectory_evaluator(conjunction: dict, actions: list[dict]) -> dict:
    return {
        "miss_distance_km": 0.25,       # computed from propagated changed orbits
        "secondary_conjunctions": []    # from re-screening all relevant objects
    }
```

The values above are only an interface example. The real function must calculate
them from propagated trajectories. It must not use a fixed km-per-m/s factor.

Each action has the shared guide fields:
`object_id`, `burn_time`, `direction`, `dv_ms`.

## Data contract

The output `risk_assessment` and `manoeuvre_plan` retain the top-level keys
and units defined in ORBI-SYNC Team Guide, Section 5.2. Times are UTC ISO 8601,
distances km, relative speeds km/s, and manoeuvre delta-v m/s.

`alternatives` contains other candidate plan objects with strategy, actions,
cost, predicted Pc, secondary checks and status for Member 3 to display.
