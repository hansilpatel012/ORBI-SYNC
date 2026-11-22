"""Small status helper; actual API call is isolated in report_generator.py."""

import os


def ai_configuration_status() -> dict:
    return {
        "api_key_configured": bool(os.getenv("OPENAI_API_KEY")),
        "model": os.getenv("OPENAI_MODEL", "gpt-5.5"),
    }
