"""Tests for Member 2 Backend Client Adapter."""

from unittest.mock import MagicMock, patch
import pytest

from backend_adapter import Member4BackendClient


class MockHttpxResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


@pytest.fixture
def client():
    return Member4BackendClient(base_url="http://mock-backend:8000", operator_key="mock-key")


def test_client_headers(client):
    headers = client.headers
    assert headers["Authorization"] == "Bearer mock-key"
    assert headers["Content-Type"] == "application/json"


def test_check_health(client):
    with patch.object(client._client, "get") as mock_get:
        mock_get.return_value = MockHttpxResponse({"status": "ok"})
        res = client.check_health()
        assert res == {"status": "ok"}
        mock_get.assert_called_with(
            "http://mock-backend:8000/health",
            params=None,
            headers=client.headers,
        )


def test_get_active_satellites(client):
    with patch.object(client._client, "get") as mock_get:
        mock_get.return_value = MockHttpxResponse({"items": [{"name": "ISS"}], "total": 1})
        res = client.get_active_satellites()
        assert res["total"] == 1
        assert res["items"][0]["name"] == "ISS"


def test_post_conjunction_event(client):
    with patch.object(client._client, "post") as mock_post:
        mock_post.return_value = MockHttpxResponse({"id": "event-123"}, status_code=201)
        res = client.post_conjunction_event(
            satellite_1_id="sat-a",
            satellite_2_id="sat-b",
            closest_approach="2026-11-25T14:30:00Z",
            miss_distance_km=0.35,
            collision_probability=0.00078,
            risk_level="CRITICAL",
        )
        assert res["id"] == "event-123"
        payload = mock_post.call_args[1]["json"]
        assert payload["satellite_1_id"] == "sat-a"
        assert payload["miss_distance_km"] == 0.35
        assert payload["risk_level"] == "critical"


def test_post_manoeuvre_plan(client):
    with patch.object(client._client, "post") as mock_post:
        mock_post.return_value = MockHttpxResponse({"id": "plan-456"}, status_code=201)
        res = client.post_manoeuvre_plan(
            satellite_id="sat-a",
            conjunction_id="event-123",
            delta_v=1.45,
            fuel_estimate=0.52,
            proposed_time="2026-11-25T08:00:00Z",
        )
        assert res["id"] == "plan-456"
        payload = mock_post.call_args[1]["json"]
        assert payload["delta_v"] == 1.45
        assert payload["status"] == "proposed"
