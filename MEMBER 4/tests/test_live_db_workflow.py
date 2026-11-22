import os
import unittest
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

# Check for explicit user authorization before running any live database integration
ALLOW_LIVE_DB_TESTS = os.getenv("ALLOW_LIVE_DB_TESTS", "").strip().lower() == "true"
ALLOW_LIVE_WRITE_TESTS = os.getenv("ALLOW_LIVE_WRITE_TESTS", "").strip().lower() == "true"


@pytest.mark.skipif(
    not ALLOW_LIVE_DB_TESTS,
    reason=(
        "Live database tests skipped for safety. "
        "Set environment variable ALLOW_LIVE_DB_TESTS=true with explicit user approval "
        "to run non-destructive integration checks against a connected Supabase database."
    ),
)
class TestLiveDatabaseIntegrationWorkflow(unittest.TestCase):
    """
    Explicitly authorized live integration test workflow.
    Guaranteed safe:
    - Skipped by default.
    - Does not modify or insert records unless ALLOW_LIVE_WRITE_TESTS=true is explicitly set.
    - Never leaks credentials or keys.
    """

    def setUp(self):
        self.client = TestClient(app)
        self.admin_key = settings.admin_api_key or settings.supabase_secret_key
        self.operator_key = settings.operator_api_key or self.admin_key
        self.admin_headers = {"Authorization": f"Bearer {self.admin_key}"} if self.admin_key else {}
        self.operator_headers = {"Authorization": f"Bearer {self.operator_key}"} if self.operator_key else {}

    def test_live_health_and_database_connectivity(self):
        """Verifies real database connectivity against Supabase PostgreSQL."""
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json(), {"status": "ok"})

        diag_headers = {}
        if settings.diagnostic_api_key:
            diag_headers["X-Diagnostic-Key"] = settings.diagnostic_api_key

        db_res = self.client.get("/health/database", headers=diag_headers)
        self.assertEqual(db_res.status_code, 200)
        body = db_res.json()
        self.assertEqual(body.get("status"), "connected")
        self.assertEqual(body.get("database"), "supabase_postgresql")
        self.assertIn("latency_ms", body)

    def test_live_read_all_six_modules(self):
        """Non-destructively reads all 6 tables from the live database."""
        endpoints = [
            "/satellites",
            "/orbital-states",
            "/conjunction-events",
            "/manoeuvre-plans",
            "/simulation-runs",
            "/sustainability-metrics",
        ]
        for ep in endpoints:
            res = self.client.get(f"{ep}?page=1&page_size=5")
            self.assertEqual(res.status_code, 200, f"Failed on endpoint {ep}")
            data = res.json()
            self.assertIn("items", data, f"Missing 'items' in {ep}")
            self.assertIn("total", data, f"Missing 'total' in {ep}")

    @pytest.mark.skipif(
        not ALLOW_LIVE_WRITE_TESTS,
        reason=(
            "Live write tests skipped. Set ALLOW_LIVE_WRITE_TESTS=true to execute "
            "transient write-and-cleanup testing on a designated test database."
        ),
    )
    def test_live_complete_synthetic_workflow(self):
        """
        Executes an end-to-end synthetic workflow across all six modules:
        1. Register two synthetic satellites (Alpha & Beta).
        2. Store an orbital state for Alpha.
        3. Create a simulated conjunction event between Alpha & Beta.
        4. Store a proposed manoeuvre plan for Alpha.
        5. Create a simulation run record.
        6. Store sustainability metrics linked to the simulation.
        7. Verify all records and relationships via GET.
        8. Clean up all synthetic records in reverse dependency order.
        """
        if not self.admin_headers:
            self.skipTest("No admin key configured to authorize write test.")

        # Entity tracking for cleanup
        created_sat_alpha = None
        created_sat_beta = None
        created_state = None
        created_conjunction = None
        created_manoeuvre = None
        created_simulation = None
        created_metric = None

        from app.db import get_supabase_client
        raw_db = get_supabase_client()

        try:
            # ------------------------------------------------------------------
            # 1. Register Synthetic Satellites
            # ------------------------------------------------------------------
            res_sat_a = self.client.post(
                "/satellites",
                json={
                    "norad_id": 999901,
                    "name": "SYNTHETIC-SAT-ALPHA [TEST-ONLY]",
                    "operator_name": "ORBI-SYNC TEST HARNESS",
                    "status": "ACTIVE",
                },
                headers=self.operator_headers,
            )
            self.assertEqual(res_sat_a.status_code, 201)
            created_sat_alpha = res_sat_a.json()["id"]

            res_sat_b = self.client.post(
                "/satellites",
                json={
                    "norad_id": 999902,
                    "name": "SYNTHETIC-DEBRIS-BETA [TEST-ONLY]",
                    "operator_name": "ORBI-SYNC TEST HARNESS",
                    "status": "INACTIVE",
                },
                headers=self.operator_headers,
            )
            self.assertEqual(res_sat_b.status_code, 201)
            created_sat_beta = res_sat_b.json()["id"]

            # ------------------------------------------------------------------
            # 2. Store Sample Orbital State
            # ------------------------------------------------------------------
            res_state = self.client.post(
                "/orbital-states",
                json={
                    "satellite_id": created_sat_alpha,
                    "epoch": "2026-11-22T04:00:00Z",
                    "position_x": 6920.5,
                    "position_y": -1150.2,
                    "position_z": 410.8,
                    "velocity_x": 0.72,
                    "velocity_y": 7.38,
                    "velocity_z": 1.95,
                    "tle_line1": "1 99991U 26999A   26326.00000000  .00010000  00000-0  10000-3 0  9991",
                    "tle_line2": "2 99991  51.6400 240.0000 0005000 120.0000 330.0000 15.70000000000018",
                },
                headers=self.operator_headers,
            )
            self.assertEqual(res_state.status_code, 201)
            created_state = res_state.json()["id"]

            # ------------------------------------------------------------------
            # 3. Create Simulated Conjunction Event
            # ------------------------------------------------------------------
            res_conj = self.client.post(
                "/conjunction-events",
                json={
                    "satellite_1_id": created_sat_alpha,
                    "satellite_2_id": created_sat_beta,
                    "closest_approach": "2026-11-25T18:00:00Z",
                    "miss_distance_km": 0.35,
                    "collision_probability": 0.00042,
                    "risk_level": "critical",
                    "status": "detected",
                },
                headers=self.operator_headers,
            )
            self.assertEqual(res_conj.status_code, 201)
            created_conjunction = res_conj.json()["id"]

            # ------------------------------------------------------------------
            # 4. Store Proposed Avoidance Manoeuvre Plan
            # ------------------------------------------------------------------
            res_plan = self.client.post(
                "/manoeuvre-plans",
                json={
                    "satellite_id": created_sat_alpha,
                    "conjunction_id": created_conjunction,
                    "delta_v": 1.25,
                    "fuel_estimate": 0.45,
                    "proposed_time": "2026-11-25T12:00:00Z",
                    "status": "proposed",
                },
                headers=self.operator_headers,
            )
            self.assertEqual(res_plan.status_code, 201)
            created_manoeuvre = res_plan.json()["id"]

            # ------------------------------------------------------------------
            # 5. Create Simulation Run
            # ------------------------------------------------------------------
            res_sim = self.client.post(
                "/simulation-runs",
                json={
                    "name": "SYNTHETIC-COLLISION-AVOIDANCE-SIM [TEST-ONLY]",
                    "status": "completed",
                    "input_data": {
                        "synthetic": True,
                        "satellites": [created_sat_alpha, created_sat_beta],
                        "propagation_model": "SGP4",
                    },
                    "result_data": {
                        "synthetic": True,
                        "conjunctions_detected": 1,
                        "avoidance_delta_v": 1.25,
                    },
                },
                headers=self.operator_headers,
            )
            self.assertEqual(res_sim.status_code, 201)
            created_simulation = res_sim.json()["id"]

            # ------------------------------------------------------------------
            # 6. Store Sustainability Metrics
            # ------------------------------------------------------------------
            res_metric = self.client.post(
                "/sustainability-metrics",
                json={
                    "simulation_id": created_simulation,
                    "total_delta_v": 1.25,
                    "estimated_fuel_saved": 0.85,
                    "avoided_close_approaches": 1,
                },
                headers=self.operator_headers,
            )
            self.assertEqual(res_metric.status_code, 201)
            created_metric = res_metric.json()["id"]

            # ------------------------------------------------------------------
            # 7. Verify Relational Retrieval
            # ------------------------------------------------------------------
            # Verify satellite
            get_sat = self.client.get(f"/satellites/{created_sat_alpha}")
            self.assertEqual(get_sat.status_code, 200)
            self.assertEqual(get_sat.json()["norad_id"], 999901)

            # Verify orbital state filtered by satellite
            get_states = self.client.get(f"/orbital-states?satellite_id={created_sat_alpha}")
            self.assertEqual(get_states.status_code, 200)
            self.assertGreaterEqual(get_states.json()["total"], 1)

            # Verify conjunction event
            get_conj = self.client.get(f"/conjunction-events/{created_conjunction}")
            self.assertEqual(get_conj.status_code, 200)
            self.assertEqual(get_conj.json()["satellite_1_id"], created_sat_alpha)

            # Verify manoeuvre plan
            get_plan = self.client.get(f"/manoeuvre-plans/{created_manoeuvre}")
            self.assertEqual(get_plan.status_code, 200)
            self.assertEqual(get_plan.json()["conjunction_id"], created_conjunction)

            # Verify simulation run
            get_sim = self.client.get(f"/simulation-runs/{created_simulation}")
            self.assertEqual(get_sim.status_code, 200)

            # Verify sustainability metric filtered by simulation
            get_met = self.client.get(f"/sustainability-metrics?simulation_id={created_simulation}")
            self.assertEqual(get_met.status_code, 200)
            self.assertEqual(get_met.json()["total"], 1)

        finally:
            # ------------------------------------------------------------------
            # 8. Clean up in reverse dependency order
            # ------------------------------------------------------------------
            cleanup_errors = []
            try:
                if created_metric:
                    raw_db.table("sustainability_metrics").delete().eq("id", created_metric).execute()
            except Exception as e:
                cleanup_errors.append(f"sustainability_metrics (ID: {created_metric}): {e}")

            try:
                if created_manoeuvre:
                    raw_db.table("manoeuvre_plans").delete().eq("id", created_manoeuvre).execute()
            except Exception as e:
                cleanup_errors.append(f"manoeuvre_plans (ID: {created_manoeuvre}): {e}")

            try:
                if created_conjunction:
                    raw_db.table("conjunction_events").delete().eq("id", created_conjunction).execute()
            except Exception as e:
                cleanup_errors.append(f"conjunction_events (ID: {created_conjunction}): {e}")

            try:
                if created_state:
                    raw_db.table("orbital_states").delete().eq("id", created_state).execute()
            except Exception as e:
                cleanup_errors.append(f"orbital_states (ID: {created_state}): {e}")

            try:
                if created_simulation:
                    raw_db.table("simulation_runs").delete().eq("id", created_simulation).execute()
            except Exception as e:
                cleanup_errors.append(f"simulation_runs (ID: {created_simulation}): {e}")

            try:
                if created_sat_alpha:
                    del_res_a = self.client.delete(f"/satellites/{created_sat_alpha}", headers=self.admin_headers)
                    if del_res_a.status_code not in (200, 404):
                        cleanup_errors.append(f"DELETE /satellites/{created_sat_alpha} returned HTTP {del_res_a.status_code}: {del_res_a.text}")
                        # Fallback to direct DB delete
                        raw_db.table("satellites").delete().eq("id", created_sat_alpha).execute()
            except Exception as e:
                cleanup_errors.append(f"satellites [Alpha] (ID: {created_sat_alpha}): {e}")

            try:
                if created_sat_beta:
                    del_res_b = self.client.delete(f"/satellites/{created_sat_beta}", headers=self.admin_headers)
                    if del_res_b.status_code not in (200, 404):
                        cleanup_errors.append(f"DELETE /satellites/{created_sat_beta} returned HTTP {del_res_b.status_code}: {del_res_b.text}")
                        # Fallback to direct DB delete
                        raw_db.table("satellites").delete().eq("id", created_sat_beta).execute()
            except Exception as e:
                cleanup_errors.append(f"satellites [Beta] (ID: {created_sat_beta}): {e}")

            # ------------------------------------------------------------------
            # 9. Verify Cleanup: Ensure zero synthetic records remain
            # ------------------------------------------------------------------
            residual_records = []
            try:
                if created_metric and raw_db.table("sustainability_metrics").select("id").eq("id", created_metric).execute().data:
                    residual_records.append(f"sustainability_metrics:{created_metric}")
                if created_manoeuvre and raw_db.table("manoeuvre_plans").select("id").eq("id", created_manoeuvre).execute().data:
                    residual_records.append(f"manoeuvre_plans:{created_manoeuvre}")
                if created_conjunction and raw_db.table("conjunction_events").select("id").eq("id", created_conjunction).execute().data:
                    residual_records.append(f"conjunction_events:{created_conjunction}")
                if created_state and raw_db.table("orbital_states").select("id").eq("id", created_state).execute().data:
                    residual_records.append(f"orbital_states:{created_state}")
                if created_simulation and raw_db.table("simulation_runs").select("id").eq("id", created_simulation).execute().data:
                    residual_records.append(f"simulation_runs:{created_simulation}")
                if created_sat_alpha and raw_db.table("satellites").select("id").eq("id", created_sat_alpha).execute().data:
                    residual_records.append(f"satellites[Alpha]:{created_sat_alpha}")
                if created_sat_beta and raw_db.table("satellites").select("id").eq("id", created_sat_beta).execute().data:
                    residual_records.append(f"satellites[Beta]:{created_sat_beta}")
            except Exception as check_err:
                cleanup_errors.append(f"Post-cleanup check error: {check_err}")

            if cleanup_errors or residual_records:
                error_msg = "\n".join([
                    "=== SYNTHETIC TEST CLEANUP FAILURE REPORT ===",
                    f"Cleanup Exceptions: {cleanup_errors or 'None'}",
                    f"Uncleaned Residual Records Still in Database: {residual_records or 'None'}",
                    "ACTION REQUIRED: Manually inspect and purge the listed records from the test database.",
                ])
                self.fail(error_msg)
