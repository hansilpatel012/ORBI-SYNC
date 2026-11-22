import os
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

# Configure test environment variables
os.environ["ENVIRONMENT"] = "development"
os.environ["ADMIN_API_KEY"] = "mock-admin-secret-key"
os.environ["OPERATOR_API_KEY"] = "mock-operator-secret-key"
os.environ["DIAGNOSTIC_API_KEY"] = "mock-diag-key"
os.environ["SUPABASE_URL"] = "https://mock-project.supabase.co"
os.environ["SUPABASE_SECRET_KEY"] = "mock-service-role-key"

from app.db import get_supabase_client
from app.main import app


class MockPostgrestResponse:
    def __init__(self, data=None, count=None):
        self.data = data if data is not None else []
        self.count = count if count is not None else (len(data) if data else 0)


def create_fluent_mock(data=None, count=None):
    """Creates a MagicMock that chains all Supabase/PostgREST query methods to itself."""
    mock = MagicMock()
    methods = [
        "table",
        "select",
        "eq",
        "neq",
        "or_",
        "lte",
        "gte",
        "ilike",
        "limit",
        "order",
        "range",
        "insert",
        "update",
        "delete",
    ]
    for method in methods:
        getattr(mock, method).return_value = mock
    mock.execute.return_value = MockPostgrestResponse(data=data, count=count)
    return mock


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    return TestClient(app)


@pytest.fixture
def admin_headers():
    return {"Authorization": "Bearer mock-admin-secret-key"}


@pytest.fixture
def operator_headers():
    return {"Authorization": "Bearer mock-operator-secret-key"}


@pytest.fixture
def mock_supabase():
    mock = create_fluent_mock()
    app.dependency_overrides[get_supabase_client] = lambda: mock
    yield mock
    app.dependency_overrides.clear()


# ==============================================================================
# 1. Health & Diagnostic Endpoints
# ==============================================================================
def test_get_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_health_database(client, mock_supabase):
    mock_supabase.execute.return_value = MockPostgrestResponse(
        data=[{"id": str(uuid4())}], count=1
    )
    response = client.get("/health/database", headers={"X-Diagnostic-Key": "mock-diag-key"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "connected"
    assert data["database"] == "supabase_postgresql"
    assert data["table_tested"] == "satellites"


# ==============================================================================
# 2. Satellites API Integration Tests
# ==============================================================================
def test_satellites_crud_flow(client, mock_supabase, operator_headers, admin_headers):
    sat_id = str(uuid4())
    sat_record = {
        "id": sat_id,
        "norad_id": 25544,
        "name": "ISS (ZARYA)",
        "operator_name": "NASA",
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. List with pagination
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[sat_record], count=1)
    res = client.get("/satellites?page=1&page_size=20")
    assert res.status_code == 200
    body = res.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert len(body["items"]) == 1

    # 2. Get by ID
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[sat_record])
    res = client.get(f"/satellites/{sat_id}")
    assert res.status_code == 200
    assert res.json()["id"] == sat_id

    # 3. Create (Post) - First check returns empty, then insert succeeds
    new_sat = dict(sat_record)
    new_sat["id"] = str(uuid4())
    new_sat["norad_id"] = 30001
    mock_supabase.execute.side_effect = [
        MockPostgrestResponse(data=[]),         # Duplicate check
        MockPostgrestResponse(data=[new_sat]),  # Insert record
    ]
    res = client.post(
        "/satellites",
        json={"norad_id": 30001, "name": "TEST-SAT-1", "operator_name": "ORBI", "status": "ACTIVE"},
        headers=operator_headers,
    )
    assert res.status_code == 201
    assert res.json()["norad_id"] == 30001

    # 4. Duplicate NORAD Conflict
    mock_supabase.execute.side_effect = None
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[{"id": sat_id}])
    res = client.post(
        "/satellites",
        json={"norad_id": 25544, "name": "DUP-SAT", "operator_name": "NASA", "status": "ACTIVE"},
        headers=operator_headers,
    )
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]

    # 5. Patch (Update)
    updated_sat = dict(sat_record)
    updated_sat["status"] = "INACTIVE"
    mock_supabase.execute.side_effect = [
        MockPostgrestResponse(data=[sat_record]),    # Existence check
        MockPostgrestResponse(data=[updated_sat]),   # Update result
    ]
    res = client.patch(f"/satellites/{sat_id}", json={"status": "INACTIVE"}, headers=operator_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "INACTIVE"

    # 6. Delete - Operator forbidden (403)
    res = client.delete(f"/satellites/{sat_id}", headers=operator_headers)
    assert res.status_code == 403

    # 7. Delete - Admin authorized (200)
    mock_supabase.execute.side_effect = [
        MockPostgrestResponse(data=[{"id": sat_id}]),  # Existence check
        MockPostgrestResponse(data=[]),                # Delete result
    ]
    res = client.delete(f"/satellites/{sat_id}", headers=admin_headers)
    assert res.status_code == 200
    assert "successfully deleted" in res.json()["message"]


# ==============================================================================
# 3. Orbital States API Integration Tests
# ==============================================================================
def test_orbital_states_flow(client, mock_supabase, operator_headers):
    sat_id = str(uuid4())
    state_id = str(uuid4())
    state_record = {
        "id": state_id,
        "satellite_id": sat_id,
        "epoch": datetime.now(timezone.utc).isoformat(),
        "position_x": 6800.0,
        "position_y": -1200.0,
        "position_z": 300.0,
        "velocity_x": 0.5,
        "velocity_y": 7.4,
        "velocity_z": 1.2,
        "tle_line1": None,
        "tle_line2": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. List
    mock_supabase.execute.side_effect = None
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[state_record], count=1)
    res = client.get(f"/orbital-states?satellite_id={sat_id}")
    assert res.status_code == 200
    assert res.json()["total"] == 1

    # 2. Get by ID
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[state_record])
    res = client.get(f"/orbital-states/{state_id}")
    assert res.status_code == 200
    assert res.json()["id"] == state_id

    # 3. Create (Post) - Satellite verified
    mock_supabase.execute.side_effect = [
        MockPostgrestResponse(data=[{"id": sat_id}]),   # Satellite existence check
        MockPostgrestResponse(data=[state_record]),     # Insert state
    ]
    res = client.post(
        "/orbital-states",
        json={
            "satellite_id": sat_id,
            "epoch": datetime.now(timezone.utc).isoformat(),
            "position_x": 6800.0,
            "position_y": -1200.0,
            "position_z": 300.0,
            "velocity_x": 0.5,
            "velocity_y": 7.4,
            "velocity_z": 1.2,
        },
        headers=operator_headers,
    )
    assert res.status_code == 201

    # 4. Create - Satellite missing FK (404)
    mock_supabase.execute.side_effect = None
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[])
    res = client.post(
        "/orbital-states",
        json={
            "satellite_id": str(uuid4()),
            "epoch": datetime.now(timezone.utc).isoformat(),
        },
        headers=operator_headers,
    )
    assert res.status_code == 404
    assert "does not exist" in res.json()["detail"]


# ==============================================================================
# 4. Conjunction Events API Integration Tests
# ==============================================================================
def test_conjunction_events_flow(client, mock_supabase, operator_headers):
    sat1_id = str(uuid4())
    sat2_id = str(uuid4())
    conj_id = str(uuid4())
    conj_record = {
        "id": conj_id,
        "satellite_1_id": sat1_id,
        "satellite_2_id": sat2_id,
        "closest_approach": datetime.now(timezone.utc).isoformat(),
        "miss_distance_km": 0.42,
        "collision_probability": 0.0003,
        "risk_level": "critical",
        "status": "detected",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. List
    mock_supabase.execute.side_effect = None
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[conj_record], count=1)
    res = client.get(f"/conjunction-events?satellite_id={sat1_id}")
    assert res.status_code == 200
    assert res.json()["total"] == 1

    # 2. Get by ID
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[conj_record])
    res = client.get(f"/conjunction-events/{conj_id}")
    assert res.status_code == 200
    assert res.json()["id"] == conj_id

    # 3. Create (Post) - Success (both satellites verified)
    mock_supabase.execute.side_effect = [
        MockPostgrestResponse(data=[{"id": sat1_id}]),  # sat1 check
        MockPostgrestResponse(data=[{"id": sat2_id}]),  # sat2 check
        MockPostgrestResponse(data=[conj_record]),      # insert
    ]
    res = client.post(
        "/conjunction-events",
        json={
            "satellite_1_id": sat1_id,
            "satellite_2_id": sat2_id,
            "closest_approach": datetime.now(timezone.utc).isoformat(),
            "miss_distance_km": 0.42,
            "collision_probability": 0.0003,
            "risk_level": "unknown",
            "status": "detected",
        },
        headers=operator_headers,
    )
    assert res.status_code == 201

    # 4. Create - Identical satellites rejected by Pydantic validator (422)
    res = client.post(
        "/conjunction-events",
        json={"satellite_1_id": sat1_id, "satellite_2_id": sat1_id},
        headers=operator_headers,
    )
    assert res.status_code == 422


# ==============================================================================
# 5. Manoeuvre Plans API Integration Tests
# ==============================================================================
def test_manoeuvre_plans_flow(client, mock_supabase, operator_headers):
    sat_id = str(uuid4())
    conj_id = str(uuid4())
    plan_id = str(uuid4())
    plan_record = {
        "id": plan_id,
        "satellite_id": sat_id,
        "conjunction_id": conj_id,
        "delta_v": 1.25,
        "fuel_estimate": 0.48,
        "proposed_time": datetime.now(timezone.utc).isoformat(),
        "status": "proposed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. List
    mock_supabase.execute.side_effect = None
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[plan_record], count=1)
    res = client.get(f"/manoeuvre-plans?satellite_id={sat_id}")
    assert res.status_code == 200

    # 2. Get by ID
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[plan_record])
    res = client.get(f"/manoeuvre-plans/{plan_id}")
    assert res.status_code == 200
    assert res.json()["delta_v"] == 1.25

    # 3. Create (Post) - Satellite and conjunction verified
    mock_supabase.execute.side_effect = [
        MockPostgrestResponse(data=[{"id": sat_id}]),   # sat check
        MockPostgrestResponse(data=[{"id": conj_id}]),  # conj check
        MockPostgrestResponse(data=[plan_record]),      # insert
    ]
    res = client.post(
        "/manoeuvre-plans",
        json={
            "satellite_id": sat_id,
            "conjunction_id": conj_id,
            "delta_v": 1.25,
            "fuel_estimate": 0.48,
            "status": "proposed",
        },
        headers=operator_headers,
    )
    assert res.status_code == 201

    # 4. Patch
    updated_plan = dict(plan_record)
    updated_plan["status"] = "approved"
    mock_supabase.execute.side_effect = [
        MockPostgrestResponse(data=[plan_record]),     # existence check
        MockPostgrestResponse(data=[updated_plan]),    # update
    ]
    res = client.patch(
        f"/manoeuvre-plans/{plan_id}",
        json={"status": "approved"},
        headers=operator_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "approved"


# ==============================================================================
# 6. Simulation Runs API Integration Tests
# ==============================================================================
def test_simulation_runs_flow(client, mock_supabase, operator_headers):
    sim_id = str(uuid4())
    sim_record = {
        "id": sim_id,
        "name": "Monte Carlo Batch A",
        "status": "pending",
        "input_data": {"steps": 100},
        "result_data": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. List
    mock_supabase.execute.side_effect = None
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[sim_record], count=1)
    res = client.get("/simulation-runs?status=pending")
    assert res.status_code == 200

    # 2. Get by ID
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[sim_record])
    res = client.get(f"/simulation-runs/{sim_id}")
    assert res.status_code == 200
    assert res.json()["name"] == "Monte Carlo Batch A"

    # 3. Create
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[sim_record])
    res = client.post(
        "/simulation-runs",
        json={"name": "Monte Carlo Batch A", "status": "pending", "input_data": {"steps": 100}},
        headers=operator_headers,
    )
    assert res.status_code == 201

    # 4. Patch
    completed_sim = dict(sim_record)
    completed_sim["status"] = "completed"
    completed_sim["result_data"] = {"collision_count": 0}
    mock_supabase.execute.side_effect = [
        MockPostgrestResponse(data=[sim_record]),      # existence check
        MockPostgrestResponse(data=[completed_sim]),   # update
    ]
    res = client.patch(
        f"/simulation-runs/{sim_id}",
        json={"status": "completed", "result_data": {"collision_count": 0}},
        headers=operator_headers,
    )
    assert res.status_code == 200
    assert res.json()["status"] == "completed"


# ==============================================================================
# 7. Sustainability Metrics API Integration Tests
# ==============================================================================
def test_sustainability_metrics_flow(client, mock_supabase, operator_headers):
    sim_id = str(uuid4())
    metric_id = str(uuid4())
    metric_record = {
        "id": metric_id,
        "simulation_id": sim_id,
        "total_delta_v": 3.8,
        "estimated_fuel_saved": 1.4,
        "avoided_close_approaches": 2,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # 1. List
    mock_supabase.execute.side_effect = None
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[metric_record], count=1)
    res = client.get(f"/sustainability-metrics?simulation_id={sim_id}")
    assert res.status_code == 200
    assert res.json()["total"] == 1

    # 2. Get by ID
    mock_supabase.execute.return_value = MockPostgrestResponse(data=[metric_record])
    res = client.get(f"/sustainability-metrics/{metric_id}")
    assert res.status_code == 200
    assert res.json()["total_delta_v"] == 3.8

    # 3. Create (Post)
    mock_supabase.execute.side_effect = [
        MockPostgrestResponse(data=[{"id": sim_id}]),  # sim check
        MockPostgrestResponse(data=[metric_record]),    # insert
    ]
    res = client.post(
        "/sustainability-metrics",
        json={
            "simulation_id": sim_id,
            "total_delta_v": 3.8,
            "estimated_fuel_saved": 1.4,
            "avoided_close_approaches": 2,
        },
        headers=operator_headers,
    )
    assert res.status_code == 201

    # 4. Patch
    updated_metric = dict(metric_record)
    updated_metric["avoided_close_approaches"] = 3
    mock_supabase.execute.side_effect = [
        MockPostgrestResponse(data=[metric_record]),     # existence check
        MockPostgrestResponse(data=[updated_metric]),    # update
    ]
    res = client.patch(
        f"/sustainability-metrics/{metric_id}",
        json={"avoided_close_approaches": 3},
        headers=operator_headers,
    )
    assert res.status_code == 200
    assert res.json()["avoided_close_approaches"] == 3


# ==============================================================================
# 8. Cross-Cutting Security & UUID Validation Tests
# ==============================================================================
@pytest.mark.parametrize(
    "path",
    [
        "/satellites/invalid-uuid",
        "/orbital-states/invalid-uuid",
        "/conjunction-events/invalid-uuid",
        "/manoeuvre-plans/invalid-uuid",
        "/simulation-runs/invalid-uuid",
        "/sustainability-metrics/invalid-uuid",
    ],
)
def test_invalid_uuid_returns_422(client, path):
    res = client.get(path)
    assert res.status_code == 422


@pytest.mark.parametrize(
    "method,path,payload",
    [
        ("post", "/satellites", {"norad_id": 1, "name": "A", "operator_name": "B"}),
        ("patch", f"/satellites/{uuid4()}", {"name": "A"}),
        ("delete", f"/satellites/{uuid4()}", None),
        ("post", "/orbital-states", {"satellite_id": str(uuid4()), "epoch": "2026-11-22T00:00:00Z"}),
        ("post", "/conjunction-events", {"satellite_1_id": str(uuid4()), "satellite_2_id": str(uuid4())}),
        ("post", "/manoeuvre-plans", {"satellite_id": str(uuid4())}),
        ("patch", f"/manoeuvre-plans/{uuid4()}", {"status": "approved"}),
        ("post", "/simulation-runs", {"name": "sim"}),
        ("patch", f"/simulation-runs/{uuid4()}", {"status": "completed"}),
        ("post", "/sustainability-metrics", {"total_delta_v": 1.0}),
        ("patch", f"/sustainability-metrics/{uuid4()}", {"total_delta_v": 2.0}),
    ],
)
def test_unauthenticated_writes_rejected_with_401(client, method, path, payload):
    if method == "post":
        res = client.post(path, json=payload)
    elif method == "patch":
        res = client.patch(path, json=payload)
    elif method == "delete":
        res = client.delete(path)
    assert res.status_code == 401
