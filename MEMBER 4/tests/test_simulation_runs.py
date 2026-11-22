import os
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import UUID, uuid4

# Set test environment configuration
os.environ["ENVIRONMENT"] = "development"
os.environ["ADMIN_API_KEY"] = "mock-admin-secret-key"
os.environ["OPERATOR_API_KEY"] = "mock-operator-secret-key"
os.environ["DIAGNOSTIC_API_KEY"] = "mock-diag-key"
os.environ["SUPABASE_URL"] = "https://mock-project.supabase.co"
os.environ["SUPABASE_SECRET_KEY"] = "mock-service-role-key"

from fastapi import HTTPException
from pydantic import ValidationError

from app.auth import AuthUser, UserRole
from app.routers.simulation_runs import (
    create_simulation_run,
    get_simulation_run,
    list_simulation_runs,
    update_simulation_run,
)
from app.schemas.simulation_run import (
    SimulationRunCreate,
    SimulationRunPagination,
    SimulationRunResponse,
    SimulationRunUpdate,
)


class MockPostgrestResponse:
    def __init__(self, data=None, count=None):
        self.data = data if data is not None else []
        self.count = count if count is not None else (len(data) if data else 0)


class MockQueryBuilder:
    """Mock query builder for Supabase PostgREST chaining."""

    def __init__(self, response: MockPostgrestResponse):
        self._response = response

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
        return self

    def gte(self, *args, **kwargs):
        return self

    def ilike(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def execute(self):
        return self._response


class TestSimulationRunsAPI(unittest.TestCase):
    def setUp(self):
        self.operator_user = AuthUser(
            id="op-1", email="op@orbi-sync.local", role=UserRole.OPERATOR.value
        )
        self.admin_user = AuthUser(
            id="admin-1", email="admin@orbi-sync.local", role=UserRole.ADMIN.value
        )

        self.run_id = uuid4()
        self.sample_run = {
            "id": self.run_id,
            "name": "Monte Carlo Conjunction Scenario Alpha",
            "status": "pending",
            "input_data": {
                "step_size_seconds": 60,
                "duration_hours": 72,
                "satellites_count": 2,
            },
            "result_data": None,
            "created_at": datetime.now(timezone.utc),
        }

    # --------------------------------------------------------------------------
    # 1. Schema Validation
    # --------------------------------------------------------------------------
    def test_simulation_run_create_valid(self):
        payload = SimulationRunCreate(
            name="LEO High Density Collision Simulation",
            status="pending",
            input_data={"propagation_steps": 1000},
        )
        self.assertEqual(payload.name, "LEO High Density Collision Simulation")
        self.assertEqual(payload.status, "pending")
        self.assertEqual(payload.input_data["propagation_steps"], 1000)

    def test_simulation_run_create_empty_name_fails(self):
        with self.assertRaises(ValidationError):
            SimulationRunCreate(name="")

    def test_simulation_run_update_empty_fails(self):
        with self.assertRaises(ValidationError):
            SimulationRunUpdate()

    # --------------------------------------------------------------------------
    # 2. GET /simulation-runs (Pagination & Filters)
    # --------------------------------------------------------------------------
    def test_list_simulation_runs_pagination(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_run], count=1)
        )

        res = list_simulation_runs(
            page=1,
            page_size=20,
            name=None,
            status_filter=None,
            start_date=None,
            end_date=None,
            client=mock_client,
        )
        self.assertIsInstance(res, SimulationRunPagination)
        self.assertEqual(res.total, 1)
        self.assertEqual(res.page, 1)
        self.assertEqual(res.page_size, 20)
        self.assertEqual(res.total_pages, 1)
        self.assertEqual(len(res.items), 1)
        self.assertEqual(res.items[0].name, "Monte Carlo Conjunction Scenario Alpha")

    def test_list_simulation_runs_with_filters(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_run], count=1)
        )

        res = list_simulation_runs(
            page=1,
            page_size=10,
            name="Monte Carlo",
            status_filter="pending",
            start_date=None,
            end_date=None,
            client=mock_client,
        )
        self.assertEqual(res.total, 1)
        self.assertEqual(res.items[0].id, self.run_id)

    # --------------------------------------------------------------------------
    # 3. GET /simulation-runs/{id}
    # --------------------------------------------------------------------------
    def test_get_simulation_run_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_run])
        )

        res = get_simulation_run(id=self.run_id, client=mock_client)
        self.assertEqual(res["id"], self.run_id)
        self.assertEqual(res["status"], "pending")

    def test_get_simulation_run_not_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            get_simulation_run(id=uuid4(), client=mock_client)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    # --------------------------------------------------------------------------
    # 4. POST /simulation-runs (Creation)
    # --------------------------------------------------------------------------
    def test_create_simulation_run_success(self):
        payload = SimulationRunCreate(
            name="Orbital Collision Probability Run #12",
            status="pending",
            input_data={"seed": 42, "samples": 50000},
        )

        created_record = {
            "id": uuid4(),
            "name": payload.name,
            "status": "pending",
            "input_data": payload.input_data,
            "result_data": None,
            "created_at": datetime.now(timezone.utc),
        }

        mock_client = MagicMock()
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            MockPostgrestResponse(data=[created_record])
        )

        res = create_simulation_run(
            payload=payload, current_user=self.operator_user, client=mock_client
        )
        self.assertEqual(res["name"], payload.name)
        self.assertEqual(res["status"], "pending")

    # --------------------------------------------------------------------------
    # 5. PATCH /simulation-runs/{id} (Update)
    # --------------------------------------------------------------------------
    def test_update_simulation_run_success(self):
        payload = SimulationRunUpdate(
            status="completed",
            result_data={
                "conjunctions_found": 2,
                "minimum_distance_km": 0.31,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        updated_record = dict(self.sample_run)
        updated_record["status"] = "completed"
        updated_record["result_data"] = payload.result_data

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[self.sample_run])
        )
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            MockPostgrestResponse(data=[updated_record])
        )

        res = update_simulation_run(
            payload=payload,
            id=self.run_id,
            current_user=self.operator_user,
            client=mock_client,
        )
        self.assertEqual(res["status"], "completed")
        self.assertEqual(res["result_data"]["conjunctions_found"], 2)

    def test_update_simulation_run_not_found(self):
        payload = SimulationRunUpdate(status="running")
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            update_simulation_run(
                payload=payload,
                id=uuid4(),
                current_user=self.operator_user,
                client=mock_client,
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
