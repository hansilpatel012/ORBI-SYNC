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
from app.routers.orbital_states import (
    create_orbital_state,
    get_orbital_state,
    list_orbital_states,
)
from app.schemas.orbital_state import (
    OrbitalStateCreate,
    OrbitalStatePagination,
    OrbitalStateResponse,
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

    def gte(self, *args, **kwargs):
        return self

    def lte(self, *args, **kwargs):
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


class TestOrbitalStatesAPI(unittest.TestCase):
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

        self.sample_sat_uuid = uuid4()
        self.sample_state_uuid = uuid4()
        self.sample_epoch = datetime.now(timezone.utc)
        self.sample_state = {
            "id": self.sample_state_uuid,
            "satellite_id": self.sample_sat_uuid,
            "epoch": self.sample_epoch,
            "position_x": 6871.5,
            "position_y": -1200.3,
            "position_z": 340.1,
            "velocity_x": 0.85,
            "velocity_y": 7.45,
            "velocity_z": 1.82,
            "tle_line1": "1 25544U 98067A   26325.50000000  .00016717  00000-0  10270-3 0  9001",
            "tle_line2": "2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537",
            "created_at": datetime.now(timezone.utc),
        }

    # --------------------------------------------------------------------------
    # 1. Pydantic Model Validation
    # --------------------------------------------------------------------------
    def test_orbital_state_create_valid(self):
        payload = OrbitalStateCreate(
            satellite_id=self.sample_sat_uuid,
            epoch=self.sample_epoch,
            position_x=6871.5,
            position_y=-1200.3,
            position_z=340.1,
            velocity_x=0.85,
            velocity_y=7.45,
            velocity_z=1.82,
        )
        self.assertEqual(payload.satellite_id, self.sample_sat_uuid)
        self.assertEqual(payload.position_x, 6871.5)
        self.assertEqual(payload.velocity_y, 7.45)

    def test_orbital_state_create_rejects_nan_and_inf(self):
        with self.assertRaises(ValidationError):
            OrbitalStateCreate(
                satellite_id=self.sample_sat_uuid,
                epoch=self.sample_epoch,
                position_x=float("nan"),
            )

        with self.assertRaises(ValidationError):
            OrbitalStateCreate(
                satellite_id=self.sample_sat_uuid,
                epoch=self.sample_epoch,
                velocity_z=float("inf"),
            )

    # --------------------------------------------------------------------------
    # 2. GET /orbital-states (Pagination & Filtering)
    # --------------------------------------------------------------------------
    def test_list_orbital_states_pagination(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_state], count=1)
        )

        res = list_orbital_states(
            page=1,
            page_size=20,
            satellite_id=None,
            start_epoch=None,
            end_epoch=None,
            client=mock_client,
        )
        self.assertIsInstance(res, OrbitalStatePagination)
        self.assertEqual(res.total, 1)
        self.assertEqual(res.page, 1)
        self.assertEqual(res.page_size, 20)
        self.assertEqual(res.total_pages, 1)
        self.assertEqual(len(res.items), 1)
        self.assertEqual(res.items[0].position_x, 6871.5)

    def test_list_orbital_states_with_satellite_filter(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_state], count=1)
        )

        res = list_orbital_states(
            page=1,
            page_size=10,
            satellite_id=self.sample_sat_uuid,
            start_epoch=None,
            end_epoch=None,
            client=mock_client,
        )
        self.assertEqual(res.total, 1)
        self.assertEqual(res.items[0].satellite_id, self.sample_sat_uuid)

    # --------------------------------------------------------------------------
    # 3. GET /orbital-states/{id}
    # --------------------------------------------------------------------------
    def test_get_orbital_state_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_state])
        )

        res = get_orbital_state(id=self.sample_state_uuid, client=mock_client)
        self.assertEqual(res["id"], self.sample_state_uuid)
        self.assertEqual(res["position_x"], 6871.5)

    def test_get_orbital_state_not_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            get_orbital_state(id=uuid4(), client=mock_client)
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("not found", ctx.exception.detail.lower())

    # --------------------------------------------------------------------------
    # 4. POST /orbital-states (Validation & Creation)
    # --------------------------------------------------------------------------
    def test_create_orbital_state_success(self):
        payload = OrbitalStateCreate(
            satellite_id=self.sample_sat_uuid,
            epoch=self.sample_epoch,
            position_x=7000.0,
            position_y=0.0,
            position_z=0.0,
            velocity_x=0.0,
            velocity_y=7.5,
            velocity_z=0.0,
            tle_line1="1 25544U 98067A   26325.50000000  .00016717  00000-0  10270-3 0  9001",
            tle_line2="2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537",
        )

        created_state = {
            "id": uuid4(),
            "satellite_id": self.sample_sat_uuid,
            "epoch": self.sample_epoch,
            "position_x": 7000.0,
            "position_y": 0.0,
            "position_z": 0.0,
            "velocity_x": 0.0,
            "velocity_y": 7.5,
            "velocity_z": 0.0,
            "tle_line1": payload.tle_line1,
            "tle_line2": payload.tle_line2,
            "created_at": datetime.now(timezone.utc),
        }

        mock_client = MagicMock()
        # Satellite check finds the satellite
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[{"id": str(self.sample_sat_uuid)}])
        )
        # Insert returns created record
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            MockPostgrestResponse(data=[created_state])
        )

        res = create_orbital_state(
            payload=payload, current_user=self.operator_user, client=mock_client
        )
        self.assertEqual(res["position_x"], 7000.0)
        self.assertEqual(res["satellite_id"], self.sample_sat_uuid)

    def test_create_orbital_state_satellite_not_found(self):
        payload = OrbitalStateCreate(
            satellite_id=uuid4(),
            epoch=self.sample_epoch,
            position_x=7000.0,
            position_y=0.0,
            position_z=0.0,
            velocity_x=0.0,
            velocity_y=7.5,
            velocity_z=0.0,
        )

        mock_client = MagicMock()
        # Satellite check returns empty (satellite does not exist)
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            create_orbital_state(
                payload=payload, current_user=self.operator_user, client=mock_client
            )
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertIn("does not exist", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
