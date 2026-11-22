import unittest
from fastapi.testclient import TestClient
from app.main import app

class TestCorsConfiguration(unittest.TestCase):
    """Verifies Cross-Origin Resource Sharing (CORS) behavior for frontend clients."""

    def setUp(self):
        self.client = TestClient(app)

    def test_cors_preflight_for_vite_localhost(self):
        """Verifies OPTIONS preflight for standard Vite dev server (http://localhost:5173)."""
        response = self.client.options(
            "/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")
        self.assertIn("GET", response.headers.get("access-control-allow-methods", ""))

    def test_cors_preflight_for_react_localhost(self):
        """Verifies OPTIONS preflight for Create React App / Next.js (http://localhost:3000)."""
        response = self.client.options(
            "/satellites",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:3000")
        self.assertEqual(response.headers.get("access-control-allow-credentials"), "true")

    def test_cors_preflight_for_loopback_ip(self):
        """Verifies OPTIONS preflight for 127.0.0.1 on custom port."""
        response = self.client.options(
            "/health",
            headers={
                "Origin": "http://127.0.0.1:8080",
                "Access-Control-Request-Method": "GET",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://127.0.0.1:8080")

    def test_cors_get_request_includes_allow_origin_header(self):
        """Verifies GET /health includes Access-Control-Allow-Origin for permitted origins."""
        response = self.client.get("/health", headers={"Origin": "http://localhost:5173"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")

    def test_cors_disallows_arbitrary_untrusted_origins(self):
        """Verifies external untrusted origins do not receive permissive CORS headers."""
        response = self.client.options(
            "/health",
            headers={
                "Origin": "https://malicious-external-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        # Should not echo back the malicious origin
        self.assertNotEqual(
            response.headers.get("access-control-allow-origin"),
            "https://malicious-external-site.com",
        )
