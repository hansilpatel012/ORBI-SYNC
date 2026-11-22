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
from app.routers.conjunction_events import (
    create_conjunction_event,
    get_conjunction_event,
    list_conjunction_events,
)
from app.schemas.conjunction_event import (
    ConjunctionEventCreate,
    ConjunctionEventPagination,
    ConjunctionEventResponse,
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

    def or_(self, *args, **kwargs):
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

    def execute(self):
        return self._response


class TestConjunctionEventsAPI(unittest.TestCase):
    def setUp(self):
        self.operator_user = AuthUser(
            id="op-1", email="op@orbi-sync.local", role=UserRole.OPERATOR.value
        )
        self.admin_user = AuthUser(
            id="admin-1", email="admin@orbi-sync.local", role=UserRole.ADMIN.value
        )
        self.viewer_user = AuthUser(
            id="viewer-1", email="viewer@orbi-sync.local", role=UserRole.VIEWER.value
        )

        self.sat_1_id = uuid4()
        self.sat_2_id = uuid4()
        self.event_id = uuid4()
        self.sample_tca = datetime.now(timezone.utc)

        self.sample_event = {
            "id": self.event_id,
            "satellite_1_id": self.sat_1_id,
            "satellite_2_id": self.sat_2_id,
            "closest_approach": self.sample_tca,
            "miss_distance_km": 0.45,
            "collision_probability": 0.00025,
            "risk_level": "critical",
            "status": "detected",
            "created_at": datetime.now(timezone.utc),
        }

    # --------------------------------------------------------------------------
    # 1. Schema Validation
    # --------------------------------------------------------------------------
    def test_conjunction_event_create_valid(self):
        payload = ConjunctionEventCreate(
            satellite_1_id=self.sat_1_id,
            satellite_2_id=self.sat_2_id,
            closest_approach=self.sample_tca,
            miss_distance_km=0.45,
            collision_probability=0.00025,
            risk_level="critical",
            status="detected",
        )
        self.assertEqual(payload.satellite_1_id, self.sat_1_id)
        self.assertEqual(payload.satellite_2_id, self.sat_2_id)
        self.assertEqual(payload.miss_distance_km, 0.45)
        self.assertEqual(payload.collision_probability, 0.00025)

    def test_conjunction_event_rejects_identical_satellites(self):
        with self.assertRaises(ValidationError):
            ConjunctionEventCreate(
                satellite_1_id=self.sat_1_id,
                satellite_2_id=self.sat_1_id,  # Identical satellites!
                miss_distance_km=0.1,
            )

    def test_conjunction_event_rejects_out_of_bounds_probability(self):
        with self.assertRaises(ValidationError):
            ConjunctionEventCreate(
                satellite_1_id=self.sat_1_id,
                satellite_2_id=self.sat_2_id,
                collision_probability=1.5,  # Must be <= 1.0
            )

        with self.assertRaises(ValidationError):
            ConjunctionEventCreate(
                satellite_1_id=self.sat_1_id,
                satellite_2_id=self.sat_2_id,
                collision_probability=-0.01,  # Must be >= 0.0
            )

    def test_conjunction_event_rejects_negative_miss_distance(self):
        with self.assertRaises(ValidationError):
            ConjunctionEventCreate(
                satellite_1_id=self.sat_1_id,
                satellite_2_id=self.sat_2_id,
                miss_distance_km=-5.0,  # Must be >= 0.0
            )

    def test_conjunction_event_rejects_nan_inf(self):
        with self.assertRaises(ValidationError):
            ConjunctionEventCreate(
                satellite_1_id=self.sat_1_id,
                satellite_2_id=self.sat_2_id,
                miss_distance_km=float("nan"),
            )

    # --------------------------------------------------------------------------
    # 2. GET /conjunction-events (Pagination & Filters)
    # --------------------------------------------------------------------------
    def test_list_conjunction_events_pagination(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_event], count=1)
        )

        res = list_conjunction_events(
            page=1,
            page_size=20,
            satellite_id=None,
            satellite_1_id=None,
            satellite_2_id=None,
            risk_level=None,
            status_filter=None,
            max_miss_distance_km=None,
            min_collision_probability=None,
            start_tca=None,
            end_tca=None,
            client=mock_client,
        )
        self.assertIsInstance(res, ConjunctionEventPagination)
        self.assertEqual(res.total, 1)
        self.assertEqual(res.page, 1)
        self.assertEqual(res.page_size, 20)
        self.assertEqual(res.total_pages, 1)
        self.assertEqual(len(res.items), 1)
        self.assertEqual(res.items[0].risk_level, "critical")

    def test_list_conjunction_events_with_filters(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_event], count=1)
        )

        res = list_conjunction_events(
            page=1,
            page_size=10,
            satellite_id=self.sat_1_id,
            satellite_1_id=None,
            satellite_2_id=None,
            risk_level="critical",
            status_filter="detected",
            max_miss_distance_km=1.0,
            min_collision_probability=0.0001,
            start_tca=None,
            end_tca=None,
            client=mock_client,
        )
        self.assertEqual(res.total, 1)
        self.assertEqual(res.items[0].id, self.event_id)

    # --------------------------------------------------------------------------
    # 3. GET /conjunction-events/{id}
    # --------------------------------------------------------------------------
    def test_get_conjunction_event_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_event])
        )

        res = get_conjunction_event(id=self.event_id, client=mock_client)
        self.assertEqual(res["id"], self.event_id)
        self.assertEqual(res["miss_distance_km"], 0.45)

    def test_get_conjunction_event_not_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            get_conjunction_event(id=uuid4(), client=mock_client)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    # --------------------------------------------------------------------------
    # 4. POST /conjunction-events (Creation & Validation)
    # --------------------------------------------------------------------------
    def test_create_conjunction_event_success(self):
        payload = ConjunctionEventCreate(
            satellite_1_id=self.sat_1_id,
            satellite_2_id=self.sat_2_id,
            closest_approach=self.sample_tca,
            miss_distance_km=0.35,
            collision_probability=0.0005,
            risk_level="unknown",  # should be auto-derived to critical
            status="detected",
        )

        created_record = {
            "id": uuid4(),
            "satellite_1_id": self.sat_1_id,
            "satellite_2_id": self.sat_2_id,
            "closest_approach": self.sample_tca,
            "miss_distance_km": 0.35,
            "collision_probability": 0.0005,
            "risk_level": "critical",
            "status": "detected",
            "created_at": datetime.now(timezone.utc),
        }

        mock_client = MagicMock()
        # Mock sat1 and sat2 existence checks
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[{"id": "exists"}])
        )
        # Mock insert
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            MockPostgrestResponse(data=[created_record])
        )

        res = create_conjunction_event(
            payload=payload, current_user=self.operator_user, client=mock_client
        )
        self.assertEqual(res["risk_level"], "critical")
        self.assertEqual(res["miss_distance_km"], 0.35)

    def test_create_conjunction_event_primary_sat_missing(self):
        payload = ConjunctionEventCreate(
            satellite_1_id=uuid4(),
            satellite_2_id=self.sat_2_id,
            miss_distance_km=2.5,
        )

        mock_client = MagicMock()
        # Primary sat check returns empty
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            create_conjunction_event(
                payload=payload, current_user=self.operator_user, client=mock_client
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("primary satellite", ctx.exception.detail.lower())

    def test_create_conjunction_event_secondary_sat_missing(self):
        payload = ConjunctionEventCreate(
            satellite_1_id=self.sat_1_id,
            satellite_2_id=uuid4(),
            miss_distance_km=2.5,
        )

        mock_client = MagicMock()
        # First call (sat1) succeeds, second call (sat2) returns empty
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.side_effect = [
            MockPostgrestResponse(data=[{"id": str(self.sat_1_id)}]),
            MockPostgrestResponse(data=[]),
        ]

        with self.assertRaises(HTTPException) as ctx:
            create_conjunction_event(
                payload=payload, current_user=self.operator_user, client=mock_client
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("secondary satellite", ctx.exception.detail.lower())


if __name__ == "__main__":
    unittest.main()
