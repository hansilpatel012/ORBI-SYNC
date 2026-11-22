from ai.report_generator import generate_ai_report


def test_local_report_is_generated_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    sample = {
        "risk_assessment": {
            "conjunction_id": "C-TEST",
            "risk_level": "HIGH",
            "collision_probability": 0.0002,
            "miss_distance_km": 0.35,
            "tca": "2026-11-23T03:12:45Z",
            "relative_speed_kms": 10.2,
        },
        "manoeuvre_plan": {"status": "NO_CERTIFIED_PLAN"},
        "anomaly_details": ["Object B TLE is stale"],
    }
    output = generate_ai_report(sample)
    assert output["mode"] == "local_fallback_no_api_key"
    assert "C-TEST" in output["report"]
    assert "0.0002" in output["report"]
    assert "Object B TLE is stale" in output["report"]


def test_report_never_calls_itself_real_ai_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    output = generate_ai_report({"risk_assessment": {}, "manoeuvre_plan": {}, "anomaly_details": []})
    assert output["mode"].startswith("local_fallback")
