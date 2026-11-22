# ORBI-SYNC System Integration Report
**Version:** 1.0.0  
**Role:** Integration Engineer  
**Date:** 2026-11-22  
**Status:** Verified & Operational  

---

## 1. Executive Summary & Integration Architecture

ORBI-SYNC is a cooperative satellite collision avoidance and space traffic intelligence platform. The workspace unites three core subsystems:
1. **MEMBER 4 (FastAPI + Supabase PostgreSQL Backend):** Central API gateway, database abstraction layer, role-based security, and data repository for the six core mission modules.
2. **member2 (Python Risk & Coordination Engine):** Encounter-plane collision probability calculator ($P_c$), rule-based anomaly detector, multi-agent maneuver planner, RTN relative geometry engine, and situational briefing reporter.
3. **frontend (Next.js 16 + CesiumJS 3D Mission Control):** Interactive 3D globe visualization, real-time telemetry tracking, ranked conjunction alerts, situation overview, and mission status monitoring.

```
+----------------------------------------------------------------------------------------------------+
|                                    ORBI-SYNC INTEGRATION TOPOLOGY                                  |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|    +-----------------------------+                 +-------------------------------+               |
|    |    Member 1: Propagation    |                 |   Member 2: Intelligence      |               |
|    |    (SGP4 Ephemeris / M1)    |                 |   (Risk & Coordination Engine)|               |
|    +--------------+--------------+                 +---------------+---------------+               |
|                   | [Pending Interface]                            |                               |
|                   | Trajectory Evaluator Callback                  | Validated Adapter             |
|                   v                                                v (member2_adapter.py)          |
|    +-------------------------------------------------------------------------------+               |
|    |                    ORBI-SYNC FastAPI Central Gateway (Member 4)               |               |
|    |                                                                               |               |
|    |    - Router /coordination (Status, Risk, Manoeuvre, Geometry, Scenarios)      |               |
|    |    - 6 Preserved Supabase PostgreSQL Modules:                                 |               |
|    |      /satellites, /orbital-states, /conjunction-events,                       |               |
|    |      /manoeuvre-plans, /simulation-runs, /sustainability-metrics              |               |
|    |    - Preserved Credentials & Test Suites (115 passed)                         |               |
|    +---------------------------------------+---------------------------------------+               |
|                                            |                                                       |
|                                            | REST API & CORS Gateway                               |
|                                            | (api-client.js / data-source.js)                      |
|                                            v                                                       |
|                        +---------------------------------------+                                   |
|                        |   Next.js 16 + CesiumJS Web Frontend  |                                   |
|                        |   - 3D Interactive Orbital Globe      |                                   |
|                        |   - Conjunction Alerts with Pc        |                                   |
|                        |   - Live Gateway & Engine Telemetry   |                                   |
|                        |   - Prominent Synthetic Data Labels   |                                   |
|                        +---------------------------------------+                                   |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Actual Data Contracts & Validated Adapters

### 2.1 Subsystem Contract Comparison

| Field / Concept | Frontend (`data/*.json`, `orbits.js`) | Member 4 Backend (`schemas/*.py`) | Member 2 Engine (`member2_engine.py`) |
| :--- | :--- | :--- | :--- |
| **Asset Identifier** | String (`orbi-sat-1`, `sim-deb-0417`) | UUID (`satellites.id`, `norad_id`) | String (`SAT-A`, `DEBRIS-B`) |
| **Epoch / TCA** | ISO UTC (`epoch`, `tcaIso`) | ISO UTC datetime (`epoch`, `closest_approach`) | ISO UTC string (`tca`) |
| **Separation** | `missDistanceKm` (float) | `miss_distance_km` (float, $\ge 0.0$) | `miss_distance_km` (float, $\ge 0.0$) |
| **Relative Velocity**| `relativeVelocityKmS` (float) | Stored in `simulation_runs.input_data` | `relative_speed_kms` (float, $\ge 0.0$) |
| **Risk Metric** | `risk`: `"critical"`, `"warning"`, `"monitor"` | `risk_level`: `"low"`, `"medium"`, `"high"`, `"critical"` | `risk_level`: `"LOW"`, `"MEDIUM"`, `"HIGH"`, `"CRITICAL"` |
| **Collision Prob.** | Originally null (`"not available"`) | `collision_probability` ($0.0 \le P_c \le 1.0$) | `pc`: Noncentral $\chi^2$ $df=2$ CDF |
| **Manoeuvre Plan** | Displayed in situational overview | `delta_v`, `fuel_estimate`, `proposed_time`, `status` | `total_dv_ms`, `actions`, `alternatives`, `fuel_cost_%` |

### 2.2 Validated Adapters Implemented

1. **Member 4 Adapter (`MEMBER 4/app/adapters/member2_adapter.py`):**
   - Implements `Member2Adapter` and validated Pydantic v2 schemas: `ConjunctionAnalysisRequest`, `RiskAssessmentResult`, `ManoeuvrePlanResult`, `RelativeGeometryRequest`, `RelativeGeometryResult`, and `FullCoordinationReport`.
   - Bridges Member 4 database entries into Member 2's encounter model.
   - Automatically handles virtual environment site-packages and dependency paths.
   - Injects the trajectory evaluator (operational callback when Member 1 is present, or synthetic evaluator with clear disclosures).

2. **Member 4 Coordination Router (`MEMBER 4/app/routers/coordination.py`):**
   - `GET /coordination/status`: Returns health, integration state, supported features, and explicit missing Member 1 dependencies.
   - `POST /coordination/assess-risk`: Validates and runs 2D Gaussian $P_c$ calculation and rule-based anomaly detection.
   - `POST /coordination/plan-manoeuvre`: Generates candidate avoidance burns with alternative rankings.
   - `POST /coordination/relative-geometry`: Computes RTN (Radial, Along-Track, Cross-Track) geometry, range, azimuth, and elevation.
   - `POST /coordination/full-analysis`: Generates complete multi-agent coordination analysis with situation report.
   - `GET /coordination/scenario-conjunctions`: Supplies pre-analyzed demonstration scenarios to the frontend.

3. **Member 2 Client Adapter (`member2/backend_adapter.py`):**
   - Implements `Member4BackendClient` using `httpx`.
   - Allows Member 2 to query active satellites (`GET /satellites?status=ACTIVE`), orbital states (`GET /orbital-states`), and post verified conjunction events (`POST /conjunction-events`), maneuver plans (`POST /manoeuvre-plans`), simulation runs (`POST /simulation-runs`), and sustainability metrics (`POST /sustainability-metrics`).

4. **Frontend API Client & Data Adapter (`frontend/lib/api-client.js`, `frontend/lib/data-source.js`):**
   - Asynchronously queries Member 4 and Member 2 coordination endpoints.
   - Gracefully merges live backend status, active satellites, and conjunction calculations into CesiumJS globe scenarios.
   - Features zero-downtime offline fallback to local mock scenario if the backend is initializing or offline.

---

## 3. Preservation of Teammates' Work & Credentials

- **Six Supabase Modules Preserved:** `satellites`, `orbital_states`, `conjunction_events`, `manoeuvre_plans`, `simulation_runs`, and `sustainability_metrics` remain 100% intact with their original routing, validations, and database connectors.
- **Security & Credentials Preserved:** All environment variables in `MEMBER 4/.env` (`SUPABASE_URL`, `SUPABASE_SECRET_KEY`, `DIAGNOSTIC_API_KEY`) remain untouched.
- **Safety Policy Upheld:** Zero destructive writes or unauthorized mutations were performed on the live Supabase database (`ALLOW_LIVE_WRITE_TESTS=false`).
- **Existing Test Suites Preserved:** All 110 original tests in Member 4 pass without modification.

---

## 4. Synthetic Data Disclosures & Safe Labeling

Per the scientific limitations documented in `member2/README.md`, all synthetic results are explicitly labeled:
- **Collision Probability ($P_c$):** Calculated using an isotropic 2D Gaussian encounter-plane model (noncentral $\chi^2$, $df=2$) under a circular hard-body assumption and team-calibrated dimensionless uncertainty scale.
- **Trajectory Evaluation:** Marked with `SYNTHETIC_EVALUATOR_WARNING`:
  > *"SYNTHETIC TEST OUTPUT: Trajectory evaluation uses a synthetic linear approximation (demo_evaluator.py). Certified collision avoidance maneuvers require Member 1's numerical propagation and secondary conjunction screening callable."*
- **Frontend Badging:** The UI highlights synthetic telemetry with `(synth)` tags and explicit hover tooltips on the close approach alert feed.

---

## 5. Verification & Test Execution Results

### 5.1 Frontend Build Check
- **Framework:** Next.js 16.4.6, React 19, CesiumJS 1.147.0
- **Command:** `cd frontend; pnpm run build`
- **Result:** **PASSED (Exit Code: 0)**
- **Details:** 3/3 static pages optimized and prerendered in 5.8s.

### 5.2 Backend Integration Test Suite
- **Environment:** Python 3.12.10, Pytest 9.2.0, AnyIO 4.16.0
- **Member 4 Test Suite:** `115 PASSED`, `3 SKIPPED` (safe live database tests), `0 FAILED` in 3.77s.
  - `test_satellites.py`: 20 passed
  - `test_conjunction_events.py`: 12 passed
  - `test_orbital_states.py`: 8 passed
  - `test_manoeuvre_plans.py`: 14 passed
  - `test_simulation_runs.py`: 11 passed
  - `test_sustainability_metrics.py`: 11 passed
  - `test_coordination_adapter.py`: 8 passed
  - `test_api_integration.py`: 25 passed
  - `test_cors.py`: 5 passed
  - `test_synthetic_workflow.py`: 1 passed
- **Member 2 Test Suite:** `20 PASSED`, `0 FAILED` in 3.22s.
  - `test_ai_report.py`: 2 passed
  - `test_backend_adapter.py`: 5 passed
  - `test_member2.py`: 8 passed
  - `test_satellite_view_geometry.py`: 5 passed

---

## 6. Startup & Run Commands (Windows PowerShell)

### Step 1: Start Member 4 FastAPI Backend Gateway
```powershell
cd "c:\Users\patel\Desktop\ORBI-SYNC\MEMBER 4"
& ".venv\Scripts\Activate.ps1"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- Interactive Swagger Documentation: `http://localhost:8000/docs`
- Health & Diagnostic Endpoint: `http://localhost:8000/health`
- Coordination Engine Status: `http://localhost:8000/coordination/status`

### Step 2: Run Member 2 Intelligence Demo & Tests
```powershell
cd "c:\Users\patel\Desktop\ORBI-SYNC\member2"
$env:PYTHONPATH = "."
& "..\MEMBER 4\.venv\Scripts\python.exe" main.py
& "..\MEMBER 4\.venv\Scripts\pytest.exe" -v tests
```

### Step 3: Start Next.js Mission Control Frontend
```powershell
cd "c:\Users\patel\Desktop\ORBI-SYNC\frontend"
pnpm run dev
```
- Open browser at: `http://localhost:3000`

---

## 7. Gap Analysis: Missing Member 1 Dependencies

To transition ORBI-SYNC from a demonstrator prototype to an operational, flight-certified collision avoidance system, Member 1 must deliver the following four components:

### 1. Physical Trajectory Evaluator Callback
- **Interface Contract:**
  ```python
  def trajectory_evaluator(conjunction: dict, actions: list[dict]) -> dict:
      """
      Applies delta-v impulses, propagates modified orbits, recomputes TCA/miss distance,
      and screens for secondary conjunctions across the satellite catalog.
      """
      return {
          "miss_distance_km": float,       # Recomputed from propagated modified orbits
          "secondary_conjunctions": list   # Encounters induced by the avoidance burn
      }
  ```
- **Current State:** Handled by `member2/demo_evaluator.py` using a synthetic linear approximation ($2.0 \times \Delta v$). This must not be used for operational decision-making.

### 2. High-Precision Numerical Propagator (SGP4 / Ephemeris)
- **Current State:** Circular two-body Keplerian orbits ($r = R_E + h$, no atmospheric drag, no $J_2$ zonal harmonics, no solar radiation pressure).
- **Required:** Numerical integrator or SGP4 ephemeris engine that periodically pushes state vectors via `POST /orbital-states`.

### 3. Full 3D Covariance Matrix ($6 \times 6$ State Covariance)
- **Current State:** Dimensionless `uncertainty_scale` multiplied by a base scalar $\sigma$ assuming isotropic encounter-plane spherical uncertainty.
- **Required:** Real position/velocity error ellipsoids projected onto the B-plane (radial, in-track, cross-track covariance) to compute authentic NASA CARA collision probabilities.

### 4. Post-Burn Catalog Secondary Screening
- **Current State:** Returns empty secondary encounter list (`[]`).
- **Required:** Broad screening of modified orbital trajectories against all cataloged objects to guarantee an avoidance maneuver does not cause a secondary conjunction.
