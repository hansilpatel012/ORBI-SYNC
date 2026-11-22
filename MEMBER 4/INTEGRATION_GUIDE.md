# ORBI-SYNC API Integration & Contract Guide
**Version:** 0.8.0  
**Backend:** FastAPI + Supabase PostgreSQL  
**Author:** Member 4 (Central Backend, API Gateway & Database Engine)  
**Target Audience:** Member 1 (Orbital Mechanics), Member 2 (Conjunction Analysis), Member 3 (Manoeuvre Planning & Sustainability), and Frontend Developers.

---

## 1. System Architecture & Team Member Workflow

```
+----------------------------------------------------------------------------------------------------+
|                                      ORBI-SYNC ARCHITECTURE                                        |
+----------------------------------------------------------------------------------------------------+
|                                                                                                    |
|    +-----------------------------+                 +-------------------------------+               |
|    |    Member 1: Propagation    |                 |   Member 2: Conjunction       |               |
|    |    (SGP4 / Ephemeris)       |                 |   (Collision Risk Predictor)  |               |
|    +--------------+--------------+                 +---------------+---------------+               |
|                   |                                                |                               |
|       POST /orbital-states                             POST /conjunction-events                    |
|                   |                                                |                               |
|                   v                                                v                               |
|    +-------------------------------------------------------------------------------+               |
|    |                    ORBI-SYNC FastAPI Central Backend (Member 4)               |               |
|    |                                                                               |               |
|    |    - CORS-enabled Gateway (Vite/React/Next.js/Streamlit)                      |               |
|    |    - Role-based Auth (Bearer token / Supabase JWT / Dev API Keys)             |               |
|    |    - Modular REST Endpoints for all 6 core tables                             |               |
|    |    - Input validation via Pydantic v2 (finite numbers, UUIDs, ISO-8601)       |               |
|    +---------------------------------------+---------------------------------------+               |
|                   ^                        |                       ^                               |
|                   |                        v                       |                               |
|       POST /manoeuvre-plans      Supabase PostgreSQL      GET /satellites, /conjunction-events    |
|       POST /simulation-runs      (Row Level Security)      (CORS REST API / React / Vite UI)       |
|       POST /sustainability-metrics         |                       |                               |
|                   |                        |                       |                               |
|    +--------------+--------------+         |       +---------------+---------------+               |
|    |    Member 3: Manoeuvre      |         |       |      Frontend Web UI          |               |
|    |    & Sustainability Engine  |         |       |  (React, Vite, Dashboard)     |               |
|    +-----------------------------+         +------>+-------------------------------+               |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Cross-Origin Resource Sharing (CORS) Configuration

The backend is pre-configured with CORS middleware to enable friction-free frontend integration during local development and testing.

### Supported Local Development Origins
Out of the box, the backend permits requests from:
* `http://localhost:3000` (Create React App / Next.js)
* `http://localhost:5173` (Vite / React / Vue)
* `http://localhost:8000` (FastAPI / Static servers)
* `http://localhost:8080` (Standard web dev port)
* `http://localhost:8501` (Streamlit analytics dashboard)
* `http://localhost:4173` (Vite preview build)
* All equivalent loopback IP origins: `http://127.0.0.1:<port>`
* Any dynamic local dev port matching the regex `^https?://(localhost|127\.0\.0\.1)(:\d+)?$`

### Configuring Custom Origins
To add custom staging or production frontend domains, define `CORS_ORIGINS` in your `.env`:
```env
CORS_ORIGINS=http://localhost:5173,https://dashboard.orbi-sync.space,https://staging.orbi-sync.space
```

### CORS Headers Returned
Preflight `OPTIONS` requests automatically return:
* `Access-Control-Allow-Origin: <Requesting Origin>`
* `Access-Control-Allow-Credentials: true`
* `Access-Control-Allow-Methods: GET, POST, PATCH, DELETE, OPTIONS`
* `Access-Control-Allow-Headers: Authorization, Content-Type, X-Diagnostic-Key`

---

## 3. Authentication & Authorization Contracts

### Role Hierarchy
| Role | Required For | Auth Method |
| :--- | :--- | :--- |
| **Viewer / Public** | All `GET` endpoints (`/satellites`, `/orbital-states`, `/conjunction-events`, etc.) and `/health` | No auth header required |
| **Operator** | All `POST` (create) and `PATCH` (update) operations across all 6 modules | `Authorization: Bearer <OPERATOR_API_KEY>` or Supabase JWT (`app_metadata.role = "operator"`) |
| **Administrator** | Destructive deletion: `DELETE /satellites/{id}` | `Authorization: Bearer <ADMIN_API_KEY>` or Supabase JWT (`app_metadata.role = "admin"`) |
| **Diagnostic** | Database connectivity check: `GET /health/database` | `X-Diagnostic-Key: <DIAGNOSTIC_API_KEY>` |

### Client Request Headers Example
```http
Authorization: Bearer dev-operator-secret-key-12345
Content-Type: application/json
```

---

## 4. Integration Specifications by Member

### Member 1: Orbital Propagation & SGP4 Ephemeris
* **Primary Role:** Computes propagated satellite state vectors from two-line element sets (TLEs) or numerical integrators and persists them.
* **Flow:**
  1. Retrieve active satellites: `GET /satellites?status=ACTIVE`
  2. For each propagation step, push state vectors: `POST /orbital-states`
* **Data Contract Specifications:**
  - `satellite_id`: UUID referencing an existing satellite in `public.satellites`.
  - `epoch`: UTC timestamp in ISO-8601 format (e.g. `2026-11-22T04:00:00Z`).
  - `position_x`, `position_y`, `position_z`: Coordinate vector in **kilometers (km)** in the TEME/ECI coordinate frame. Must be finite numbers (no `NaN` or `Inf`).
  - `velocity_x`, `velocity_y`, `velocity_z`: Velocity components in **kilometers per second (km/s)** in TEME/ECI.
  - `tle_line1`, `tle_line2`: Optional raw NORAD TLE lines used for propagation.

---

### Member 2: Conjunction Analysis & Collision Prediction
* **Primary Role:** Ingests latest orbital states of satellite pairs, calculates Time of Closest Approach (TCA), computes collision probabilities, and registers conjunction events.
* **Flow:**
  1. Query recent orbital states: `GET /orbital-states?satellite_id=<id>`
  2. Compute miss distance and collision probability ($P_c$).
  3. Register detected conjunctions: `POST /conjunction-events`
  4. Query active conjunctions for real-time monitoring: `GET /conjunction-events?status=detected&risk_level=critical`
* **Data Contract Specifications:**
  - `satellite_1_id`: Primary asset UUID (`satellites.id`).
  - `satellite_2_id`: Secondary asset or debris object UUID (`satellites.id`). Must be **distinct** from `satellite_1_id`.
  - `closest_approach`: Predicted UTC timestamp of closest approach.
  - `miss_distance_km`: Minimum distance in **kilometers (km)** ($\ge 0.0$).
  - `collision_probability`: Calculated collision probability ($0.0 \le P_c \le 1.0$).
  - `risk_level`: Risk tier: `"low"`, `"medium"`, `"high"`, `"critical"`, or `"unknown"`.
  - `status`: Lifecycle status: `"detected"`, `"monitoring"`, `"mitigated"`, `"resolved"`, or `"dismissed"`.

---

### Member 3: Manoeuvre Planning & Space Sustainability
* **Primary Role:** Generates optimal collision avoidance burns ($\Delta v$), estimates propellant consumption, logs simulation runs, and computes sustainability indices.
* **Flow:**
  1. Query critical events: `GET /conjunction-events?status=detected&risk_level=critical`
  2. Optimize avoidance trajectory and submit plan: `POST /manoeuvre-plans`
  3. Create simulation record: `POST /simulation-runs`
  4. Update simulation status and results: `PATCH /simulation-runs/{id}`
  5. Compute and store sustainability metrics: `POST /sustainability-metrics`
  6. Update manoeuvre status upon execution: `PATCH /manoeuvre-plans/{id}` (`"approved"`, `"executing"`, `"completed"`)
* **Data Contract Specifications:**
  - **Manoeuvre Plans:**
    - `satellite_id`: Maneuvering satellite UUID.
    - `conjunction_id`: Conjunction event UUID being mitigated (nullable).
    - `delta_v`: Velocity impulse in **m/s** or **km/s** ($\ge 0.0$).
    - `fuel_estimate`: Propellant consumption in **kilograms (kg)** ($\ge 0.0$).
    - `proposed_time`: Planned execution time in ISO-8601 UTC.
    - `status`: `"proposed"`, `"approved"`, `"executing"`, `"completed"`, `"cancelled"`, `"rejected"`.
  - **Simulation Runs:**
    - `name`: Simulation title string.
    - `status`: `"pending"`, `"running"`, `"completed"`, `"failed"`.
    - `input_data`: Arbitrary JSONB object storing parameters, step size, duration, algorithms.
    - `result_data`: Arbitrary JSONB object storing trajectories, outputs, execution time.
  - **Sustainability Metrics:**
    - `simulation_id`: UUID referencing `public.simulation_runs` (nullable).
    - `total_delta_v`: Cumulative delta-v expended across maneuvers ($\ge 0.0$).
    - `estimated_fuel_saved`: Propellant saved via optimization in kg ($\ge 0.0$).
    - `avoided_close_approaches`: Count of averted close encounters ($\ge 0$).

---

### Frontend Developers: Dashboard & UI Integration
* **Primary Role:** Displays interactive 3D satellite tracks, alerts operators to conjunctions, shows manoeuvre approval buttons, and visualizes sustainability graphs.
* **Pagination Pattern:**
  All list endpoints support `page` ($\ge 1$, default: 1) and `page_size` ($\ge 1$, $\le 100$, default: 20).
  Response envelope:
  ```json
  {
    "items": [...],
    "total": 42,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
  ```

---

## 5. Module Endpoints & Example JSON Responses

### 5.1 Satellites API (`/satellites`)

#### `GET /satellites` (Paginated List)
* **Query Parameters:** `page=1&page_size=20&status=ACTIVE&operator_name=NASA`
* **Response `200 OK`:**
```json
{
  "items": [
    {
      "id": "a0270ae3-43c6-40dc-a41a-5f609b8ec6b4",
      "norad_id": 25544,
      "name": "ISS (ZARYA)",
      "operator_name": "International Space Station Partners",
      "status": "ACTIVE",
      "created_at": "2026-11-20T18:40:12.184321Z"
    },
    {
      "id": "7c82e6d1-4209-41e8-a1cb-569d67e1a001",
      "norad_id": 48274,
      "name": "STARLINK-2305",
      "operator_name": "SpaceX",
      "status": "ACTIVE",
      "created_at": "2026-11-21T09:15:30.412000Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

#### `POST /satellites` (Register Satellite)
* **Headers:** `Authorization: Bearer <OPERATOR_API_KEY>`, `Content-Type: application/json`
* **Request Payload:**
```json
{
  "norad_id": 48274,
  "name": "STARLINK-2305",
  "operator_name": "SpaceX",
  "status": "ACTIVE"
}
```
* **Response `201 Created`:**
```json
{
  "id": "7c82e6d1-4209-41e8-a1cb-569d67e1a001",
  "norad_id": 48274,
  "name": "STARLINK-2305",
  "operator_name": "SpaceX",
  "status": "ACTIVE",
  "created_at": "2026-11-22T04:15:00.123456Z"
}
```

---

### 5.2 Orbital States API (`/orbital-states`)

#### `GET /orbital-states` (Paginated List)
* **Query Parameters:** `page=1&page_size=10&satellite_id=a0270ae3-43c6-40dc-a41a-5f609b8ec6b4`
* **Response `200 OK`:**
```json
{
  "items": [
    {
      "id": "e81d7f42-99c0-449a-b425-6cb3de4210a9",
      "satellite_id": "a0270ae3-43c6-40dc-a41a-5f609b8ec6b4",
      "epoch": "2026-11-22T04:00:00Z",
      "position_x": 6871.45,
      "position_y": -1245.18,
      "position_z": 340.82,
      "velocity_x": 0.852,
      "velocity_y": 7.421,
      "velocity_z": 1.834,
      "tle_line1": "1 25544U 98067A   26325.50000000  .00016717  00000-0  10270-3 0  9001",
      "tle_line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537",
      "created_at": "2026-11-22T04:00:05.819201Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

#### `POST /orbital-states` (Submit State Vector)
* **Headers:** `Authorization: Bearer <OPERATOR_API_KEY>`, `Content-Type: application/json`
* **Request Payload:**
```json
{
  "satellite_id": "a0270ae3-43c6-40dc-a41a-5f609b8ec6b4",
  "epoch": "2026-11-22T04:00:00Z",
  "position_x": 6871.45,
  "position_y": -1245.18,
  "position_z": 340.82,
  "velocity_x": 0.852,
  "velocity_y": 7.421,
  "velocity_z": 1.834,
  "tle_line1": "1 25544U 98067A   26325.50000000  .00016717  00000-0  10270-3 0  9001",
  "tle_line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"
}
```
* **Response `201 Created`:**
```json
{
  "id": "e81d7f42-99c0-449a-b425-6cb3de4210a9",
  "satellite_id": "a0270ae3-43c6-40dc-a41a-5f609b8ec6b4",
  "epoch": "2026-11-22T04:00:00Z",
  "position_x": 6871.45,
  "position_y": -1245.18,
  "position_z": 340.82,
  "velocity_x": 0.852,
  "velocity_y": 7.421,
  "velocity_z": 1.834,
  "tle_line1": "1 25544U 98067A   26325.50000000  .00016717  00000-0  10270-3 0  9001",
  "tle_line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537",
  "created_at": "2026-11-22T04:00:05.819201Z"
}
```

---

### 5.3 Conjunction Events API (`/conjunction-events`)

#### `POST /conjunction-events` (Log Conjunction Prediction)
* **Headers:** `Authorization: Bearer <OPERATOR_API_KEY>`, `Content-Type: application/json`
* **Request Payload:**
```json
{
  "satellite_1_id": "a0270ae3-43c6-40dc-a41a-5f609b8ec6b4",
  "satellite_2_id": "7c82e6d1-4209-41e8-a1cb-569d67e1a001",
  "closest_approach": "2026-11-25T14:45:00Z",
  "miss_distance_km": 0.385,
  "collision_probability": 0.00078,
  "risk_level": "critical",
  "status": "detected"
}
```
* **Response `201 Created`:**
```json
{
  "id": "3b29c910-8b17-4ef2-a7bc-91e84a921d74",
  "satellite_1_id": "a0270ae3-43c6-40dc-a41a-5f609b8ec6b4",
  "satellite_2_id": "7c82e6d1-4209-41e8-a1cb-569d67e1a001",
  "closest_approach": "2026-11-25T14:45:00Z",
  "miss_distance_km": 0.385,
  "collision_probability": 0.00078,
  "risk_level": "critical",
  "status": "detected",
  "created_at": "2026-11-22T04:16:30.912801Z"
}
```

#### `GET /conjunction-events/{id}`
* **Response `200 OK`:** (Matches above `ConjunctionEventResponse` schema).

---

### 5.4 Manoeuvre Plans API (`/manoeuvre-plans`)

#### `POST /manoeuvre-plans` (Submit Avoidance Plan)
* **Headers:** `Authorization: Bearer <OPERATOR_API_KEY>`, `Content-Type: application/json`
* **Request Payload:**
```json
{
  "satellite_id": "a0270ae3-43c6-40dc-a41a-5f609b8ec6b4",
  "conjunction_id": "3b29c910-8b17-4ef2-a7bc-91e84a921d74",
  "delta_v": 1.45,
  "fuel_estimate": 0.52,
  "proposed_time": "2026-11-25T08:00:00Z",
  "status": "proposed"
}
```
* **Response `201 Created`:**
```json
{
  "id": "5f1a2389-1e24-4d89-9a3b-287d10e54b61",
  "satellite_id": "a0270ae3-43c6-40dc-a41a-5f609b8ec6b4",
  "conjunction_id": "3b29c910-8b17-4ef2-a7bc-91e84a921d74",
  "delta_v": 1.45,
  "fuel_estimate": 0.52,
  "proposed_time": "2026-11-25T08:00:00Z",
  "status": "proposed",
  "created_at": "2026-11-22T04:18:10.512390Z"
}
```

#### `PATCH /manoeuvre-plans/{id}` (Update Plan Status)
* **Headers:** `Authorization: Bearer <OPERATOR_API_KEY>`, `Content-Type: application/json`
* **Request Payload:**
```json
{
  "status": "approved"
}
```
* **Response `200 OK`:**
```json
{
  "id": "5f1a2389-1e24-4d89-9a3b-287d10e54b61",
  "satellite_id": "a0270ae3-43c6-40dc-a41a-5f609b8ec6b4",
  "conjunction_id": "3b29c910-8b17-4ef2-a7bc-91e84a921d74",
  "delta_v": 1.45,
  "fuel_estimate": 0.52,
  "proposed_time": "2026-11-25T08:00:00Z",
  "status": "approved",
  "created_at": "2026-11-22T04:18:10.512390Z"
}
```

---

### 5.5 Simulation Runs API (`/simulation-runs`)

#### `POST /simulation-runs` (Create Simulation Record)
* **Headers:** `Authorization: Bearer <OPERATOR_API_KEY>`, `Content-Type: application/json`
* **Request Payload:**
```json
{
  "name": "Monte-Carlo-LEO-Conjunction-Batch-12",
  "status": "running",
  "input_data": {
    "step_size_seconds": 60,
    "duration_hours": 72,
    "satellites": ["a0270ae3-43c6-40dc-a41a-5f609b8ec6b4", "7c82e6d1-4209-41e8-a1cb-569d67e1a001"],
    "propagation_model": "SGP4"
  }
}
```
* **Response `201 Created`:**
```json
{
  "id": "9d81e742-5f10-482a-b152-4720e981bc09",
  "name": "Monte-Carlo-LEO-Conjunction-Batch-12",
  "status": "running",
  "input_data": {
    "step_size_seconds": 60,
    "duration_hours": 72,
    "satellites": ["a0270ae3-43c6-40dc-a41a-5f609b8ec6b4", "7c82e6d1-4209-41e8-a1cb-569d67e1a001"],
    "propagation_model": "SGP4"
  },
  "result_data": null,
  "created_at": "2026-11-22T04:20:00.182741Z"
}
```

#### `PATCH /simulation-runs/{id}` (Save Results)
* **Headers:** `Authorization: Bearer <OPERATOR_API_KEY>`, `Content-Type: application/json`
* **Request Payload:**
```json
{
  "status": "completed",
  "result_data": {
    "conjunctions_detected": 1,
    "minimum_miss_distance_km": 0.385,
    "avoidance_delta_v": 1.45,
    "execution_time_seconds": 18.4,
    "completed_at": "2026-11-22T04:21:30Z"
  }
}
```
* **Response `200 OK`:** (Returns updated `SimulationRunResponse`).

---

### 5.6 Sustainability Metrics API (`/sustainability-metrics`)

#### `POST /sustainability-metrics` (Log Sustainability Performance)
* **Headers:** `Authorization: Bearer <OPERATOR_API_KEY>`, `Content-Type: application/json`
* **Request Payload:**
```json
{
  "simulation_id": "9d81e742-5f10-482a-b152-4720e981bc09",
  "total_delta_v": 1.45,
  "estimated_fuel_saved": 0.95,
  "avoided_close_approaches": 1
}
```
* **Response `201 Created`:**
```json
{
  "id": "14e7a829-3b91-4cf1-83da-0129bc81e720",
  "simulation_id": "9d81e742-5f10-482a-b152-4720e981bc09",
  "total_delta_v": 1.45,
  "estimated_fuel_saved": 0.95,
  "avoided_close_approaches": 1,
  "created_at": "2026-11-22T04:22:15.341908Z"
}
```

#### `GET /sustainability-metrics` (Filtered by Simulation)
* **Query Parameters:** `page=1&page_size=10&simulation_id=9d81e742-5f10-482a-b152-4720e981bc09`
* **Response `200 OK`:**
```json
{
  "items": [
    {
      "id": "14e7a829-3b91-4cf1-83da-0129bc81e720",
      "simulation_id": "9d81e742-5f10-482a-b152-4720e981bc09",
      "total_delta_v": 1.45,
      "estimated_fuel_saved": 0.95,
      "avoided_close_approaches": 1,
      "created_at": "2026-11-22T04:22:15.341908Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "total_pages": 1
}
```

---

## 6. Code Examples for Integration

### Python Client (Member 1, 2, or 3)
```python
import requests

BASE_URL = "http://localhost:8000"
OPERATOR_KEY = "dev-operator-secret-key-12345"

headers = {
    "Authorization": f"Bearer {OPERATOR_KEY}",
    "Content-Type": "application/json",
}

# 1. Fetch active satellites
response = requests.get(f"{BASE_URL}/satellites?status=ACTIVE")
satellites = response.json()["items"]
sat_id = satellites[0]["id"]

# 2. Push an orbital state (Member 1)
orbital_state_data = {
    "satellite_id": sat_id,
    "epoch": "2026-11-22T04:30:00Z",
    "position_x": 6870.2,
    "position_y": -1250.4,
    "position_z": 355.1,
    "velocity_x": 0.86,
    "velocity_y": 7.41,
    "velocity_z": 1.84,
}
res_state = requests.post(f"{BASE_URL}/orbital-states", json=orbital_state_data, headers=headers)
print("Orbital State Stored:", res_state.json())
```

### TypeScript / JavaScript (React / Vite Frontend)
```typescript
const BASE_URL = "http://localhost:8000";

interface Satellite {
  id: string;
  norad_id: number;
  name: string;
  operator_name: string;
  status: string;
  created_at: string;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// Fetch satellites with credentials/CORS
export async function getSatellites(page = 1, pageSize = 20): Promise<PaginatedResponse<Satellite>> {
  const res = await fetch(`${BASE_URL}/satellites?page=${page}&page_size=${pageSize}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
    credentials: "include", // Supported by CORS allow_credentials=True
  });

  if (!res.ok) {
    throw new Error(`Failed to fetch satellites: ${res.statusText}`);
  }
  return res.json();
}
```

---

## 7. Interactive Documentation (Swagger / OpenAPI)
* **Interactive UI (Swagger):** `http://localhost:8000/docs`
* **Alternative Spec UI (ReDoc):** `http://localhost:8000/redoc`
* **Raw OpenAPI JSON Spec:** `http://localhost:8000/openapi.json`
