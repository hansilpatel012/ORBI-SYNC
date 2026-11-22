"""Transparent rule-based data-quality checks for Member 2."""

from __future__ import annotations
from math import isfinite
from config import STALE_TLE_HOURS


def detect_anomalies(conjunction: dict, stale_tle_hours: float = STALE_TLE_HOURS) -> dict:
    flags = []

    for key in ("conjunction_id", "object_a", "object_b", "tca",
                "miss_distance_km", "relative_speed_kms", "data_quality"):
        if key not in conjunction:
            flags.append(f"Missing required field: {key}")

    if "miss_distance_km" in conjunction:
        value = conjunction["miss_distance_km"]
        if not isinstance(value, (int, float)) or not isfinite(float(value)) or value < 0:
            flags.append("Invalid miss_distance_km")

    if "relative_speed_kms" in conjunction:
        value = conjunction["relative_speed_kms"]
        if not isinstance(value, (int, float)) or not isfinite(float(value)) or value < 0:
            flags.append("Invalid relative_speed_kms")

    dq = conjunction.get("data_quality", {})
    for key in ("tle_age_a_h", "tle_age_b_h"):
        age = dq.get(key)
        if age is None:
            flags.append(f"Missing data_quality.{key}")
        elif not isinstance(age, (int, float)) or not isfinite(float(age)) or age < 0:
            flags.append(f"Invalid data_quality.{key}")
        elif age > stale_tle_hours:
            flags.append(f"Stale TLE: {key}={age}h")

    scale = dq.get("uncertainty_scale")
    if scale is None or not isinstance(scale, (int, float)) or not isfinite(float(scale)) or scale <= 0:
        flags.append("Missing or invalid uncertainty_scale")

    return {"anomaly_flag": bool(flags), "flags": flags}
