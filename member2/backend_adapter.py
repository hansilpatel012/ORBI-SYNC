"""Member 2 Backend Integration Adapter.

Provides validated client methods for Member 2 to communicate with Member 4's
FastAPI gateway and Supabase PostgreSQL backend.

Conforms strictly to ORBI-SYNC Integration Guide Section 5 and Section 6.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None  # type: ignore

DEFAULT_BACKEND_URL = os.getenv("ORBI_BACKEND_URL", "http://localhost:8000")
DEFAULT_OPERATOR_KEY = os.getenv("OPERATOR_API_KEY", "dev-operator-secret-key-12345")


class Member4BackendClient:
    """HTTP client adapter connecting Member 2 with Member 4 FastAPI backend."""

    def __init__(
        self,
        base_url: str = DEFAULT_BACKEND_URL,
        operator_key: str = DEFAULT_OPERATOR_KEY,
        timeout: float = 5.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.operator_key = operator_key
        self.timeout = timeout
        if httpx is not None:
            self._client = httpx.Client(timeout=timeout)
        else:
            self._client = None

    @property
    def headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.operator_key:
            headers["Authorization"] = f"Bearer {self.operator_key}"
        return headers

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if self._client:
            resp = self._client.get(url, params=params, headers=self.headers)
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError("httpx package is required for Member4BackendClient.")

    def _post(self, path: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        if self._client:
            resp = self._client.post(url, json=json_data, headers=self.headers)
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError("httpx package is required for Member4BackendClient.")

    def check_health(self) -> Dict[str, Any]:
        """Checks backend health endpoint."""
        return self._get("/health")

    def get_coordination_status(self) -> Dict[str, Any]:
        """Fetches coordination and Member 2 engine status from Member 4."""
        return self._get("/coordination/status")

    def get_active_satellites(self, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Fetches active satellite catalog from Member 4."""
        return self._get(
            "/satellites",
            params={"status": "ACTIVE", "page": page, "page_size": page_size},
        )

    def get_orbital_states(self, satellite_id: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        """Fetches latest propagated orbital states for a satellite."""
        return self._get(
            "/orbital-states",
            params={"satellite_id": str(satellite_id), "page": page, "page_size": page_size},
        )

    def post_conjunction_event(
        self,
        satellite_1_id: str,
        satellite_2_id: str,
        closest_approach: str,
        miss_distance_km: float,
        collision_probability: float,
        risk_level: str,
        status: str = "detected",
    ) -> Dict[str, Any]:
        """Submits an evaluated conjunction event prediction to Member 4."""
        payload = {
            "satellite_1_id": str(satellite_1_id),
            "satellite_2_id": str(satellite_2_id),
            "closest_approach": closest_approach,
            "miss_distance_km": round(float(miss_distance_km), 4),
            "collision_probability": max(0.0, min(1.0, float(collision_probability))),
            "risk_level": risk_level.lower(),
            "status": status.lower(),
        }
        return self._post("/conjunction-events", payload)

    def post_manoeuvre_plan(
        self,
        satellite_id: str,
        conjunction_id: Optional[str],
        delta_v: float,
        fuel_estimate: float,
        proposed_time: str,
        status: str = "proposed",
    ) -> Dict[str, Any]:
        """Submits an optimized avoidance manoeuvre plan to Member 4."""
        payload = {
            "satellite_id": str(satellite_id),
            "conjunction_id": str(conjunction_id) if conjunction_id else None,
            "delta_v": max(0.0, float(delta_v)),
            "fuel_estimate": max(0.0, float(fuel_estimate)),
            "proposed_time": proposed_time,
            "status": status.lower(),
        }
        return self._post("/manoeuvre-plans", payload)

    def post_simulation_run(
        self,
        name: str,
        input_data: Dict[str, Any],
        result_data: Optional[Dict[str, Any]] = None,
        status: str = "completed",
    ) -> Dict[str, Any]:
        """Logs a simulation run record with input parameters and results."""
        payload = {
            "name": name,
            "status": status.lower(),
            "input_data": input_data,
            "result_data": result_data,
        }
        return self._post("/simulation-runs", payload)

    def post_sustainability_metric(
        self,
        simulation_id: Optional[str],
        total_delta_v: float,
        estimated_fuel_saved: float,
        avoided_close_approaches: int,
    ) -> Dict[str, Any]:
        """Logs space sustainability metrics for a manoeuvre simulation."""
        payload = {
            "simulation_id": str(simulation_id) if simulation_id else None,
            "total_delta_v": max(0.0, float(total_delta_v)),
            "estimated_fuel_saved": max(0.0, float(estimated_fuel_saved)),
            "avoided_close_approaches": max(0, int(avoided_close_approaches)),
        }
        return self._post("/sustainability-metrics", payload)
