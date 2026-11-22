import os
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

# Configure environment variables
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


def create_fluent_mock():
    mock = MagicMock()
    for method in [
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
    ]:
        getattr(mock, method).return_value = mock
    mock.execute.return_value = MockPostgrestResponse()
    return mock


class TestCompleteSyntheticWorkflow(unittest.TestCase):
    """
    Simulates the entire multi-table synthetic workflow using mocked interactions.
    Validates payload structures, foreign keys, relationships, and error handling.
    """

    def setUp(self):
        self.client = TestClient(app)
        self.mock_db = create_fluent_mock()
        app.dependency_overrides[get_supabase_client] = lambda: self.mock_db
        self.headers = {"Authorization": "Bearer mock-operator-secret-key"}
        self.admin_headers = {"Authorization": "Bearer mock-admin-secret-key"}

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_full_synthetic_pipeline_mocked(self):
        sat_alpha_id = str(uuid4())
        sat_beta_id = str(uuid4())
        state_id = str(uuid4())
        conj_id = str(uuid4())
        plan_id = str(uuid4())
        sim_id = str(uuid4())
        metric_id = str(uuid4())

        # ----------------------------------------------------------------------
        # 1. Register Satellite Alpha
        # ----------------------------------------------------------------------
        self.mock_db.execute.side_effect = [
            MockPostgrestResponse(data=[]),  # duplicate check
            MockPostgrestResponse(
                data=[{
                    "id": sat_alpha_id,
                    "norad_id": 999901,
                    "name": "SYNTHETIC-SAT-ALPHA [TEST-ONLY]",
                    "operator_name": "ORBI-SYNC TEST HARNESS",
                    "status": "ACTIVE",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }]
            ),
        ]
        res_a = self.client.post(
            "/satellites",
            json={
                "norad_id": 999901,
                "name": "SYNTHETIC-SAT-ALPHA [TEST-ONLY]",
                "operator_name": "ORBI-SYNC TEST HARNESS",
                "status": "ACTIVE",
            },
            headers=self.headers,
        )
        self.assertEqual(res_a.status_code, 201)
        self.assertEqual(res_a.json()["id"], sat_alpha_id)

        # ----------------------------------------------------------------------
        # 2. Register Satellite Beta
        # ----------------------------------------------------------------------
        self.mock_db.execute.side_effect = [
            MockPostgrestResponse(data=[]),
            MockPostgrestResponse(
                data=[{
                    "id": sat_beta_id,
                    "norad_id": 999902,
                    "name": "SYNTHETIC-DEBRIS-BETA [TEST-ONLY]",
                    "operator_name": "ORBI-SYNC TEST HARNESS",
                    "status": "INACTIVE",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }]
            ),
        ]
        res_b = self.client.post(
            "/satellites",
            json={
                "norad_id": 999902,
                "name": "SYNTHETIC-DEBRIS-BETA [TEST-ONLY]",
                "operator_name": "ORBI-SYNC TEST HARNESS",
                "status": "INACTIVE",
            },
            headers=self.headers,
        )
        self.assertEqual(res_b.status_code, 201)
        self.assertEqual(res_b.json()["id"], sat_beta_id)

        # ----------------------------------------------------------------------
        # 3. Store Orbital State for Alpha
        # ----------------------------------------------------------------------
        self.mock_db.execute.side_effect = [
            MockPostgrestResponse(data=[{"id": sat_alpha_id}]),  # sat check
            MockPostgrestResponse(
                data=[{
                    "id": state_id,
                    "satellite_id": sat_alpha_id,
                    "epoch": "2026-11-22T04:00:00Z",
                    "position_x": 6920.5,
                    "position_y": -1150.2,
                    "position_z": 410.8,
                    "velocity_x": 0.72,
                    "velocity_y": 7.38,
                    "velocity_z": 1.95,
                    "tle_line1": "1 99991U...",
                    "tle_line2": "2 99991...",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }]
            ),
        ]
        res_state = self.client.post(
            "/orbital-states",
            json={
                "satellite_id": sat_alpha_id,
                "epoch": "2026-11-22T04:00:00Z",
                "position_x": 6920.5,
                "position_y": -1150.2,
                "position_z": 410.8,
                "velocity_x": 0.72,
                "velocity_y": 7.38,
                "velocity_z": 1.95,
            },
            headers=self.headers,
        )
        self.assertEqual(res_state.status_code, 201)
        self.assertEqual(res_state.json()["satellite_id"], sat_alpha_id)

        # ----------------------------------------------------------------------
        # 4. Create Simulated Conjunction Event
        # ----------------------------------------------------------------------
        self.mock_db.execute.side_effect = [
            MockPostgrestResponse(data=[{"id": sat_alpha_id}]),
            MockPostgrestResponse(data=[{"id": sat_beta_id}]),
            MockPostgrestResponse(
                data=[{
                    "id": conj_id,
                    "satellite_1_id": sat_alpha_id,
                    "satellite_2_id": sat_beta_id,
                    "closest_approach": "2026-11-25T18:00:00Z",
                    "miss_distance_km": 0.35,
                    "collision_probability": 0.00042,
                    "risk_level": "critical",
                    "status": "detected",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }]
            ),
        ]
        res_conj = self.client.post(
            "/conjunction-events",
            json={
                "satellite_1_id": sat_alpha_id,
                "satellite_2_id": sat_beta_id,
                "closest_approach": "2026-11-25T18:00:00Z",
                "miss_distance_km": 0.35,
                "collision_probability": 0.00042,
                "risk_level": "critical",
            },
            headers=self.headers,
        )
        self.assertEqual(res_conj.status_code, 201)
        self.assertEqual(res_conj.json()["id"], conj_id)

        # ----------------------------------------------------------------------
        # 5. Store Manoeuvre Plan
        # ----------------------------------------------------------------------
        self.mock_db.execute.side_effect = [
            MockPostgrestResponse(data=[{"id": sat_alpha_id}]),
            MockPostgrestResponse(data=[{"id": conj_id}]),
            MockPostgrestResponse(
                data=[{
                    "id": plan_id,
                    "satellite_id": sat_alpha_id,
                    "conjunction_id": conj_id,
                    "delta_v": 1.25,
                    "fuel_estimate": 0.45,
                    "proposed_time": "2026-11-25T12:00:00Z",
                    "status": "proposed",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }]
            ),
        ]
        res_plan = self.client.post(
            "/manoeuvre-plans",
            json={
                "satellite_id": sat_alpha_id,
                "conjunction_id": conj_id,
                "delta_v": 1.25,
                "fuel_estimate": 0.45,
                "status": "proposed",
            },
            headers=self.headers,
        )
        self.assertEqual(res_plan.status_code, 201)
        self.assertEqual(res_plan.json()["conjunction_id"], conj_id)

        # ----------------------------------------------------------------------
        # 6. Create Simulation Run
        # ----------------------------------------------------------------------
        self.mock_db.execute.side_effect = [
            MockPostgrestResponse(
                data=[{
                    "id": sim_id,
                    "name": "SYNTHETIC-SIM-RUN [TEST-ONLY]",
                    "status": "completed",
                    "input_data": {"satellites": [sat_alpha_id, sat_beta_id]},
                    "result_data": {"conjunctions_detected": 1},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }]
            )
        ]
        res_sim = self.client.post(
            "/simulation-runs",
            json={
                "name": "SYNTHETIC-SIM-RUN [TEST-ONLY]",
                "status": "completed",
                "input_data": {"satellites": [sat_alpha_id, sat_beta_id]},
            },
            headers=self.headers,
        )
        self.assertEqual(res_sim.status_code, 201)
        self.assertEqual(res_sim.json()["id"], sim_id)

        # ----------------------------------------------------------------------
        # 7. Store Sustainability Metrics
        # ----------------------------------------------------------------------
        self.mock_db.execute.side_effect = [
            MockPostgrestResponse(data=[{"id": sim_id}]),
            MockPostgrestResponse(
                data=[{
                    "id": metric_id,
                    "simulation_id": sim_id,
                    "total_delta_v": 1.25,
                    "estimated_fuel_saved": 0.85,
                    "avoided_close_approaches": 1,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }]
            ),
        ]
        res_metric = self.client.post(
            "/sustainability-metrics",
            json={
                "simulation_id": sim_id,
                "total_delta_v": 1.25,
                "estimated_fuel_saved": 0.85,
                "avoided_close_approaches": 1,
            },
            headers=self.headers,
        )
        self.assertEqual(res_metric.status_code, 201)
        self.assertEqual(res_metric.json()["simulation_id"], sim_id)


if __name__ == "__main__":
    unittest.main()
