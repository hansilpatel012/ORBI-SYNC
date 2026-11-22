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
from app.routers.manoeuvre_plans import (
    create_manoeuvre_plan,
    get_manoeuvre_plan,
    list_manoeuvre_plans,
    update_manoeuvre_plan,
)
from app.schemas.manoeuvre_plan import (
    ManoeuvrePlanCreate,
    ManoeuvrePlanPagination,
    ManoeuvrePlanResponse,
    ManoeuvrePlanUpdate,
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


class TestManoeuvrePlansAPI(unittest.TestCase):
    def setUp(self):
        self.operator_user = AuthUser(
            id="op-1", email="op@orbi-sync.local", role=UserRole.OPERATOR.value
        )
        self.admin_user = AuthUser(
            id="admin-1", email="admin@orbi-sync.local", role=UserRole.ADMIN.value
        )

        self.sat_id = uuid4()
        self.conj_id = uuid4()
        self.plan_id = uuid4()
        self.proposed_time = datetime.now(timezone.utc)

        self.sample_plan = {
            "id": self.plan_id,
            "satellite_id": self.sat_id,
            "conjunction_id": self.conj_id,
            "delta_v": 1.25,
            "fuel_estimate": 0.45,
            "proposed_time": self.proposed_time,
            "status": "proposed",
            "created_at": datetime.now(timezone.utc),
        }

    # --------------------------------------------------------------------------
    # 1. Schema Validation
    # --------------------------------------------------------------------------
    def test_manoeuvre_plan_create_valid(self):
        payload = ManoeuvrePlanCreate(
            satellite_id=self.sat_id,
            conjunction_id=self.conj_id,
            delta_v=1.25,
            fuel_estimate=0.45,
            proposed_time=self.proposed_time,
            status="proposed",
        )
        self.assertEqual(payload.satellite_id, self.sat_id)
        self.assertEqual(payload.delta_v, 1.25)
        self.assertEqual(payload.fuel_estimate, 0.45)

    def test_manoeuvre_plan_create_rejects_negative_delta_v(self):
        with self.assertRaises(ValidationError):
            ManoeuvrePlanCreate(
                satellite_id=self.sat_id,
                delta_v=-0.5,
            )

    def test_manoeuvre_plan_create_rejects_negative_fuel(self):
        with self.assertRaises(ValidationError):
            ManoeuvrePlanCreate(
                satellite_id=self.sat_id,
                fuel_estimate=-1.0,
            )

    def test_manoeuvre_plan_create_rejects_nan_inf(self):
        with self.assertRaises(ValidationError):
            ManoeuvrePlanCreate(
                satellite_id=self.sat_id,
                delta_v=float("nan"),
            )

    def test_manoeuvre_plan_update_empty_fails(self):
        with self.assertRaises(ValidationError):
            ManoeuvrePlanUpdate()

    # --------------------------------------------------------------------------
    # 2. GET /manoeuvre-plans (Pagination & Filters)
    # --------------------------------------------------------------------------
    def test_list_manoeuvre_plans_pagination(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_plan], count=1)
        )

        res = list_manoeuvre_plans(
            page=1,
            page_size=20,
            satellite_id=None,
            conjunction_id=None,
            status_filter=None,
            start_time=None,
            end_time=None,
            client=mock_client,
        )
        self.assertIsInstance(res, ManoeuvrePlanPagination)
        self.assertEqual(res.total, 1)
        self.assertEqual(res.page, 1)
        self.assertEqual(res.page_size, 20)
        self.assertEqual(res.total_pages, 1)
        self.assertEqual(len(res.items), 1)
        self.assertEqual(res.items[0].delta_v, 1.25)

    def test_list_manoeuvre_plans_with_filters(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_plan], count=1)
        )

        res = list_manoeuvre_plans(
            page=1,
            page_size=10,
            satellite_id=self.sat_id,
            conjunction_id=self.conj_id,
            status_filter="proposed",
            start_time=None,
            end_time=None,
            client=mock_client,
        )
        self.assertEqual(res.total, 1)
        self.assertEqual(res.items[0].id, self.plan_id)

    # --------------------------------------------------------------------------
    # 3. GET /manoeuvre-plans/{id}
    # --------------------------------------------------------------------------
    def test_get_manoeuvre_plan_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_plan])
        )

        res = get_manoeuvre_plan(id=self.plan_id, client=mock_client)
        self.assertEqual(res["id"], self.plan_id)
        self.assertEqual(res["delta_v"], 1.25)

    def test_get_manoeuvre_plan_not_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            get_manoeuvre_plan(id=uuid4(), client=mock_client)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    # --------------------------------------------------------------------------
    # 4. POST /manoeuvre-plans (Creation & Validation)
    # --------------------------------------------------------------------------
    def test_create_manoeuvre_plan_success(self):
        payload = ManoeuvrePlanCreate(
            satellite_id=self.sat_id,
            conjunction_id=self.conj_id,
            delta_v=2.1,
            fuel_estimate=0.8,
            proposed_time=self.proposed_time,
            status="proposed",
        )

        created_record = {
            "id": uuid4(),
            "satellite_id": self.sat_id,
            "conjunction_id": self.conj_id,
            "delta_v": 2.1,
            "fuel_estimate": 0.8,
            "proposed_time": self.proposed_time,
            "status": "proposed",
            "created_at": datetime.now(timezone.utc),
        }

        mock_client = MagicMock()
        # Mock sat and conjunction existence checks
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[{"id": "exists"}])
        )
        # Mock insert
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            MockPostgrestResponse(data=[created_record])
        )

        res = create_manoeuvre_plan(
            payload=payload, current_user=self.operator_user, client=mock_client
        )
        self.assertEqual(res["delta_v"], 2.1)
        self.assertEqual(res["fuel_estimate"], 0.8)

    def test_create_manoeuvre_plan_satellite_not_found(self):
        payload = ManoeuvrePlanCreate(
            satellite_id=uuid4(),
            delta_v=1.0,
        )

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            create_manoeuvre_plan(
                payload=payload, current_user=self.operator_user, client=mock_client
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("satellite", ctx.exception.detail.lower())

    def test_create_manoeuvre_plan_conjunction_not_found(self):
        payload = ManoeuvrePlanCreate(
            satellite_id=self.sat_id,
            conjunction_id=uuid4(),
            delta_v=1.0,
        )

        mock_client = MagicMock()
        # First call (sat check) succeeds, second call (conjunction check) returns empty
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
            MockPostgrestResponse(data=[{"id": str(self.sat_id)}]),
            MockPostgrestResponse(data=[]),
        ]

        with self.assertRaises(HTTPException) as ctx:
            create_manoeuvre_plan(
                payload=payload, current_user=self.operator_user, client=mock_client
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("conjunction event", ctx.exception.detail.lower())

    # --------------------------------------------------------------------------
    # 5. PATCH /manoeuvre-plans/{id} (Update)
    # --------------------------------------------------------------------------
    def test_update_manoeuvre_plan_success(self):
        payload = ManoeuvrePlanUpdate(
            status="approved",
            delta_v=2.5,
        )
        updated_record = dict(self.sample_plan)
        updated_record["status"] = "approved"
        updated_record["delta_v"] = 2.5

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[self.sample_plan])
        )
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            MockPostgrestResponse(data=[updated_record])
        )

        res = update_manoeuvre_plan(
            payload=payload,
            id=self.plan_id,
            current_user=self.operator_user,
            client=mock_client,
        )
        self.assertEqual(res["status"], "approved")
        self.assertEqual(res["delta_v"], 2.5)

    def test_update_manoeuvre_plan_not_found(self):
        payload = ManoeuvrePlanUpdate(status="approved")
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            update_manoeuvre_plan(
                payload=payload,
                id=uuid4(),
                current_user=self.operator_user,
                client=mock_client,
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
