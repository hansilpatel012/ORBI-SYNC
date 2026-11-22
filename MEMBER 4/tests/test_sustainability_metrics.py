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
from app.routers.sustainability_metrics import (
    create_sustainability_metric,
    get_sustainability_metric,
    list_sustainability_metrics,
    update_sustainability_metric,
)
from app.schemas.sustainability_metric import (
    SustainabilityMetricCreate,
    SustainabilityMetricPagination,
    SustainabilityMetricResponse,
    SustainabilityMetricUpdate,
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


class TestSustainabilityMetricsAPI(unittest.TestCase):
    def setUp(self):
        self.operator_user = AuthUser(
            id="op-1", email="op@orbi-sync.local", role=UserRole.OPERATOR.value
        )
        self.admin_user = AuthUser(
            id="admin-1", email="admin@orbi-sync.local", role=UserRole.ADMIN.value
        )

        self.sim_id = uuid4()
        self.metric_id = uuid4()
        self.sample_metric = {
            "id": self.metric_id,
            "simulation_id": self.sim_id,
            "total_delta_v": 4.85,
            "estimated_fuel_saved": 1.72,
            "avoided_close_approaches": 3,
            "created_at": datetime.now(timezone.utc),
        }

    # --------------------------------------------------------------------------
    # 1. Schema Validation
    # --------------------------------------------------------------------------
    def test_sustainability_metric_create_valid(self):
        payload = SustainabilityMetricCreate(
            simulation_id=self.sim_id,
            total_delta_v=4.85,
            estimated_fuel_saved=1.72,
            avoided_close_approaches=3,
        )
        self.assertEqual(payload.simulation_id, self.sim_id)
        self.assertEqual(payload.total_delta_v, 4.85)
        self.assertEqual(payload.estimated_fuel_saved, 1.72)
        self.assertEqual(payload.avoided_close_approaches, 3)

    def test_sustainability_metric_create_rejects_negative_values(self):
        with self.assertRaises(ValidationError):
            SustainabilityMetricCreate(total_delta_v=-1.0)

        with self.assertRaises(ValidationError):
            SustainabilityMetricCreate(estimated_fuel_saved=-0.5)

        with self.assertRaises(ValidationError):
            SustainabilityMetricCreate(avoided_close_approaches=-1)

    def test_sustainability_metric_create_rejects_nan_inf(self):
        with self.assertRaises(ValidationError):
            SustainabilityMetricCreate(total_delta_v=float("nan"))

        with self.assertRaises(ValidationError):
            SustainabilityMetricCreate(estimated_fuel_saved=float("inf"))

    def test_sustainability_metric_update_empty_fails(self):
        with self.assertRaises(ValidationError):
            SustainabilityMetricUpdate()

    # --------------------------------------------------------------------------
    # 2. GET /sustainability-metrics (Pagination & Filters)
    # --------------------------------------------------------------------------
    def test_list_sustainability_metrics_pagination(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_metric], count=1)
        )

        res = list_sustainability_metrics(
            page=1,
            page_size=20,
            simulation_id=None,
            min_avoided_approaches=None,
            min_fuel_saved=None,
            max_delta_v=None,
            start_date=None,
            end_date=None,
            client=mock_client,
        )
        self.assertIsInstance(res, SustainabilityMetricPagination)
        self.assertEqual(res.total, 1)
        self.assertEqual(res.page, 1)
        self.assertEqual(res.page_size, 20)
        self.assertEqual(res.total_pages, 1)
        self.assertEqual(len(res.items), 1)
        self.assertEqual(res.items[0].total_delta_v, 4.85)

    def test_list_sustainability_metrics_with_filters(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_metric], count=1)
        )

        res = list_sustainability_metrics(
            page=1,
            page_size=10,
            simulation_id=self.sim_id,
            min_avoided_approaches=2,
            min_fuel_saved=1.0,
            max_delta_v=5.0,
            start_date=None,
            end_date=None,
            client=mock_client,
        )
        self.assertEqual(res.total, 1)
        self.assertEqual(res.items[0].id, self.metric_id)

    # --------------------------------------------------------------------------
    # 3. GET /sustainability-metrics/{id}
    # --------------------------------------------------------------------------
    def test_get_sustainability_metric_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_metric])
        )

        res = get_sustainability_metric(id=self.metric_id, client=mock_client)
        self.assertEqual(res["id"], self.metric_id)
        self.assertEqual(res["total_delta_v"], 4.85)

    def test_get_sustainability_metric_not_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            get_sustainability_metric(id=uuid4(), client=mock_client)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    # --------------------------------------------------------------------------
    # 4. POST /sustainability-metrics (Creation & Validation)
    # --------------------------------------------------------------------------
    def test_create_sustainability_metric_success(self):
        payload = SustainabilityMetricCreate(
            simulation_id=self.sim_id,
            total_delta_v=3.5,
            estimated_fuel_saved=1.2,
            avoided_close_approaches=2,
        )

        created_record = {
            "id": uuid4(),
            "simulation_id": self.sim_id,
            "total_delta_v": 3.5,
            "estimated_fuel_saved": 1.2,
            "avoided_close_approaches": 2,
            "created_at": datetime.now(timezone.utc),
        }

        mock_client = MagicMock()
        # Mock simulation check exists
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[{"id": str(self.sim_id)}])
        )
        # Mock insert
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            MockPostgrestResponse(data=[created_record])
        )

        res = create_sustainability_metric(
            payload=payload, current_user=self.operator_user, client=mock_client
        )
        self.assertEqual(res["total_delta_v"], 3.5)
        self.assertEqual(res["avoided_close_approaches"], 2)

    def test_create_sustainability_metric_simulation_not_found(self):
        payload = SustainabilityMetricCreate(
            simulation_id=uuid4(),
            total_delta_v=3.5,
        )

        mock_client = MagicMock()
        # Simulation check returns empty
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            create_sustainability_metric(
                payload=payload, current_user=self.operator_user, client=mock_client
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("simulation run", ctx.exception.detail.lower())

    # --------------------------------------------------------------------------
    # 5. PATCH /sustainability-metrics/{id} (Update)
    # --------------------------------------------------------------------------
    def test_update_sustainability_metric_success(self):
        payload = SustainabilityMetricUpdate(
            avoided_close_approaches=5,
            estimated_fuel_saved=2.1,
        )
        updated_record = dict(self.sample_metric)
        updated_record["avoided_close_approaches"] = 5
        updated_record["estimated_fuel_saved"] = 2.1

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[self.sample_metric])
        )
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            MockPostgrestResponse(data=[updated_record])
        )

        res = update_sustainability_metric(
            payload=payload,
            id=self.metric_id,
            current_user=self.operator_user,
            client=mock_client,
        )
        self.assertEqual(res["avoided_close_approaches"], 5)
        self.assertEqual(res["estimated_fuel_saved"], 2.1)

    def test_update_sustainability_metric_not_found(self):
        payload = SustainabilityMetricUpdate(avoided_close_approaches=4)
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            update_sustainability_metric(
                payload=payload,
                id=uuid4(),
                current_user=self.operator_user,
                client=mock_client,
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
