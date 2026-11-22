import os
from pathlib import Path
from dotenv import load_dotenv

# Resolve root directory of the project where .env lives
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILENAME = os.getenv("ENV_FILE", ".env")
ENV_FILE = BASE_DIR / ENV_FILENAME

# Load environment variables from .env file if present
load_dotenv(dotenv_path=ENV_FILE)


class Settings:
    """Application configuration loaded from environment variables."""

    @property
    def supabase_url(self) -> str:
        return os.getenv("TEST_SUPABASE_URL", "").strip() or os.getenv("SUPABASE_URL", "").strip()

    @property
    def supabase_secret_key(self) -> str:
        return os.getenv("TEST_SUPABASE_SECRET_KEY", "").strip() or os.getenv("SUPABASE_SECRET_KEY", "").strip()

    @property
    def environment(self) -> str:
        return os.getenv("ENVIRONMENT", "development").strip().lower()

    @property
    def diagnostic_api_key(self) -> str:
        return os.getenv("DIAGNOSTIC_API_KEY", "").strip()

    @property
    def admin_api_key(self) -> str:
        """Dedicated API key granting admin role, fallback to DIAGNOSTIC_API_KEY."""
        return os.getenv("ADMIN_API_KEY", "").strip() or self.diagnostic_api_key

    @property
    def operator_api_key(self) -> str:
        """Dedicated API key granting operator role."""
        return os.getenv("OPERATOR_API_KEY", "").strip()

    @property
    def cors_origins(self) -> list[str]:
        """Allowed origins for CORS (comma-separated via CORS_ORIGINS)."""
        raw = os.getenv("CORS_ORIGINS", "").strip()
        if raw:
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        return [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
            "http://localhost:8080",
            "http://localhost:8501",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8501",
        ]

    @property
    def cors_origin_regex(self) -> str:
        """Regex pattern allowing any localhost or loopback port for frontend development."""
        return os.getenv("CORS_ORIGIN_REGEX", r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$").strip()

    @property
    def is_supabase_configured(self) -> bool:
        """Returns True if both Supabase URL and Secret Key are provided."""
        return bool(self.supabase_url and self.supabase_secret_key)

    def __repr__(self) -> str:
        """Safe representation that prevents accidental credential leakage in logs."""
        return (
            f"<Settings environment={self.environment!r} "
            f"supabase_configured={self.is_supabase_configured} "
            f"diagnostic_protected={bool(self.diagnostic_api_key)}>"
        )


settings = Settings()
