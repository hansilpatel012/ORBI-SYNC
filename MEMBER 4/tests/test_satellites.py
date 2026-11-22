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

from fastapi import HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import ValidationError

from app.auth import (
    AuthUser,
    UserRole,
    get_current_user,
    require_admin,
    require_operator,
)
from app.routers.health import database_health_check, health_check
from app.routers.satellites import (
    create_satellite,
    delete_satellite,
    get_satellite,
    list_satellites,
    update_satellite,
)
from app.schemas.satellite import (
    SatelliteCreate,
    SatellitePagination,
    SatelliteResponse,
    SatelliteUpdate,
)


class MockPostgrestResponse:
    def __init__(self, data=None, count=None):
        self.data = data if data is not None else []
        self.count = count if count is not None else (len(data) if data else 0)


class MockQueryBuilder:
    """Mock chaining for Supabase table queries."""

    def __init__(self, response: MockPostgrestResponse):
        self._response = response

    def select(self, *args, **kwargs):
        return self

    def eq(self, *args, **kwargs):
        return self

    def neq(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def order(self, *args, **kwargs):
        return self

    def range(self, *args, **kwargs):
        return self

    def ilike(self, *args, **kwargs):
        return self

    def insert(self, *args, **kwargs):
        return self

    def update(self, *args, **kwargs):
        return self

    def delete(self, *args, **kwargs):
        return self

    def execute(self):
        return self._response


class TestSatelliteManagementAPI(unittest.TestCase):
    def setUp(self):
        self.admin_user = AuthUser(
            id="admin-1", email="admin@orbi-sync.local", role=UserRole.ADMIN.value
        )
        self.operator_user = AuthUser(
            id="op-1", email="op@orbi-sync.local", role=UserRole.OPERATOR.value
        )
        self.viewer_user = AuthUser(
            id="viewer-1", email="viewer@orbi-sync.local", role=UserRole.VIEWER.value
        )

        self.sample_uuid = uuid4()
        self.sample_satellite = {
            "id": self.sample_uuid,
            "norad_id": 25544,
            "name": "ISS (ZARYA)",
            "operator_name": "NASA",
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc),
        }

    # --------------------------------------------------------------------------
    # 1. Pydantic Models & Validation
    # --------------------------------------------------------------------------
    def test_satellite_create_validation_success(self):
        payload = SatelliteCreate(
            norad_id=25544,
            name="ISS (ZARYA)",
            operator_name="NASA",
            status="ACTIVE",
        )
        self.assertEqual(payload.norad_id, 25544)
        self.assertEqual(payload.name, "ISS (ZARYA)")

    def test_satellite_create_invalid_norad_id(self):
        with self.assertRaises(ValidationError):
            SatelliteCreate(
                norad_id=0,  # ge=1 violated
                name="Invalid Satellite",
                operator_name="ESA",
            )

    def test_satellite_update_requires_at_least_one_field(self):
        with self.assertRaises(ValidationError):
            SatelliteUpdate()  # Empty payload must be rejected

    def test_satellite_update_valid_partial(self):
        update = SatelliteUpdate(name="ISS (NEW NAME)")
        self.assertEqual(update.name, "ISS (NEW NAME)")
        self.assertIsNone(update.status)

    # --------------------------------------------------------------------------
    # 2. Authentication & Role-Based Authorization
    # --------------------------------------------------------------------------
    def test_auth_unauthenticated_rejected(self):
        with self.assertRaises(HTTPException) as ctx:
            get_current_user(None)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_auth_admin_api_key_resolves_admin_role(self):
        creds = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="mock-admin-secret-key"
        )
        user = get_current_user(creds)
        self.assertEqual(user.role, "admin")
        self.assertTrue(user.is_admin())

    def test_auth_operator_api_key_resolves_operator_role(self):
        creds = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="mock-operator-secret-key"
        )
        user = get_current_user(creds)
        self.assertEqual(user.role, "operator")
        self.assertTrue(user.is_operator())

    def test_role_enforcement_operator_allows_both(self):
        check_operator = require_operator
        # Both admin and operator should pass require_operator
        self.assertEqual(check_operator(self.admin_user).role, "admin")
        self.assertEqual(check_operator(self.operator_user).role, "operator")

        # Viewer role must fail
        with self.assertRaises(HTTPException) as ctx:
            check_operator(self.viewer_user)
        self.assertEqual(ctx.exception.status_code, 403)

    def test_role_enforcement_admin_strictly_requires_admin(self):
        check_admin = require_admin
        # Admin passes
        self.assertEqual(check_admin(self.admin_user).role, "admin")

        # Operator fails
        with self.assertRaises(HTTPException) as ctx:
            check_admin(self.operator_user)
        self.assertEqual(ctx.exception.status_code, 403)

    # --------------------------------------------------------------------------
    # 3. GET /satellites (Pagination & Filtering)
    # --------------------------------------------------------------------------
    def test_list_satellites_pagination(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_satellite], count=1)
        )

        res = list_satellites(
            page=1,
            page_size=20,
            status_filter=None,
            operator_name=None,
            client=mock_client,
        )
        self.assertIsInstance(res, SatellitePagination)
        self.assertEqual(res.total, 1)
        self.assertEqual(res.page, 1)
        self.assertEqual(res.page_size, 20)
        self.assertEqual(res.total_pages, 1)
        self.assertEqual(len(res.items), 1)
        self.assertEqual(res.items[0].norad_id, 25544)

    # --------------------------------------------------------------------------
    # 4. GET /satellites/{id}
    # --------------------------------------------------------------------------
    def test_get_satellite_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[self.sample_satellite])
        )

        res = get_satellite(id=self.sample_uuid, client=mock_client)
        self.assertEqual(res["id"], self.sample_uuid)
        self.assertEqual(res["name"], "ISS (ZARYA)")

    def test_get_satellite_not_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            get_satellite(id=uuid4(), client=mock_client)
        self.assertEqual(ctx.exception.status_code, 404)

    # --------------------------------------------------------------------------
    # 5. POST /satellites (Create & Duplicate Handling)
    # --------------------------------------------------------------------------
    def test_create_satellite_success(self):
        payload = SatelliteCreate(
            norad_id=40001,
            name="ORBI-1",
            operator_name="ORBI-SYNC",
            status="ACTIVE",
        )
        created_record = {
            "id": uuid4(),
            "norad_id": 40001,
            "name": "ORBI-1",
            "operator_name": "ORBI-SYNC",
            "status": "ACTIVE",
            "created_at": datetime.now(timezone.utc),
        }

        mock_client = MagicMock()
        # Duplicate check returns empty
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[])
        )
        # Insert returns created record
        mock_client.table.return_value.insert.return_value.execute.return_value = (
            MockPostgrestResponse(data=[created_record])
        )

        res = create_satellite(
            payload=payload, current_user=self.operator_user, client=mock_client
        )
        self.assertEqual(res["norad_id"], 40001)
        self.assertEqual(res["name"], "ORBI-1")

    def test_create_satellite_duplicate_norad_conflict(self):
        payload = SatelliteCreate(
            norad_id=25544,
            name="Duplicate ISS",
            operator_name="NASA",
            status="ACTIVE",
        )

        mock_client = MagicMock()
        # Duplicate check finds existing record
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[{"id": str(self.sample_uuid)}])
        )

        with self.assertRaises(HTTPException) as ctx:
            create_satellite(
                payload=payload, current_user=self.operator_user, client=mock_client
            )
        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("already exists", ctx.exception.detail)

    # --------------------------------------------------------------------------
    # 6. PATCH /satellites/{id} (Update)
    # --------------------------------------------------------------------------
    def test_update_satellite_success(self):
        payload = SatelliteUpdate(status="INACTIVE")
        updated_record = dict(self.sample_satellite)
        updated_record["status"] = "INACTIVE"

        mock_client = MagicMock()
        # Existence check returns existing
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[self.sample_satellite])
        )
        # Update returns modified record
        mock_client.table.return_value.update.return_value.eq.return_value.execute.return_value = (
            MockPostgrestResponse(data=[updated_record])
        )

        res = update_satellite(
            payload=payload,
            id=self.sample_uuid,
            current_user=self.operator_user,
            client=mock_client,
        )
        self.assertEqual(res["status"], "INACTIVE")

    def test_update_satellite_not_found(self):
        payload = SatelliteUpdate(status="INACTIVE")
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            update_satellite(
                payload=payload,
                id=uuid4(),
                current_user=self.operator_user,
                client=mock_client,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    # --------------------------------------------------------------------------
    # 7. DELETE /satellites/{id} (Admin-Only Deletion)
    # --------------------------------------------------------------------------
    def test_delete_satellite_admin_success(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[{"id": str(self.sample_uuid)}])
        )
        mock_client.table.return_value.delete.return_value.eq.return_value.execute.return_value = (
            MockPostgrestResponse(data=[])
        )

        res = delete_satellite(
            id=self.sample_uuid,
            current_user=self.admin_user,
            client=mock_client,
        )
        self.assertIn("successfully deleted", res["message"])
        self.assertEqual(res["id"], str(self.sample_uuid))

    def test_delete_satellite_not_found(self):
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = (
            MockPostgrestResponse(data=[])
        )

        with self.assertRaises(HTTPException) as ctx:
            delete_satellite(
                id=uuid4(),
                current_user=self.admin_user,
                client=mock_client,
            )
        self.assertEqual(ctx.exception.status_code, 404)

    # --------------------------------------------------------------------------
    # 8. Health Endpoints Preservation
    # --------------------------------------------------------------------------
    def test_health_check_preserved(self):
        res = health_check()
        self.assertEqual(res, {"status": "ok"})

    def test_database_health_diagnostic_check(self):
        mock_client = MagicMock()
        mock_client.table.return_value = MockQueryBuilder(
            MockPostgrestResponse(data=[{"id": str(self.sample_uuid)}], count=1)
        )

        with unittest.mock.patch("app.routers.health.check_database_connection") as mock_conn:
            mock_conn.return_value = {
                "status": "connected",
                "database": "supabase_postgresql",
                "table_tested": "satellites",
                "latency_ms": 15.2,
                "record_count": 1,
                "tables_registered": ["satellites"],
            }
            dummy_response = Response()
            res = database_health_check(dummy_response)
            self.assertEqual(res["status"], "connected")
            self.assertEqual(res["database"], "supabase_postgresql")


if __name__ == "__main__":
    unittest.main()
