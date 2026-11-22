"""Risk scoring using a simple isotropic 2D Gaussian encounter-plane model.

This implements the simple 2D Gaussian approach requested in ORBI-SYNC Team
Guide, Section 6, Member 2. It is a prototype approximation, NOT a complete
operational Pc implementation. It assumes circular hard-body region and
isotropic encounter-plane uncertainty sigma^2 * I.

For an offset 2D Gaussian, squared radial distance / sigma^2 follows a
noncentral chi-square distribution with 2 degrees of freedom:
Pc = F_ncx2((R/sigma)^2; df=2, nc=(d/sigma)^2).

The shared guide schema has only uncertainty_scale, not covariance. We
therefore convert it to sigma using a configurable base sigma. Calibrate that
base with Member 1 / operator-provided covariance before making real claims.
"""

from __future__ import annotations
from math import isfinite
from scipy.stats import ncx2

from config import (
    BASE_SIGMA_KM,
    DEFAULT_COMBINED_RADIUS_KM,
    RISK_THRESHOLDS,
)


def calculate_pc_2d(
    miss_distance_km: float,
    combined_radius_km: float,
    sigma_km: float,
) -> float:
    """Return 2D Gaussian collision probability under stated assumptions."""
    values = (miss_distance_km, combined_radius_km, sigma_km)
    if not all(isfinite(float(v)) for v in values):
        raise ValueError("Pc inputs must be finite numbers.")
    if miss_distance_km < 0:
        raise ValueError("miss_distance_km cannot be negative.")
    if combined_radius_km <= 0:
        raise ValueError("combined_radius_km must be positive.")
    if sigma_km <= 0:
        raise ValueError("sigma_km must be positive.")

    x = (combined_radius_km / sigma_km) ** 2
    noncentrality = (miss_distance_km / sigma_km) ** 2
    pc = float(ncx2.cdf(x, df=2, nc=noncentrality))
    return min(1.0, max(0.0, pc))


def classify_risk(pc: float) -> str:
    if not isfinite(float(pc)) or not 0.0 <= pc <= 1.0:
        raise ValueError("pc must be a finite probability between 0 and 1.")
    if pc < RISK_THRESHOLDS["low_max"]:
        return "LOW"
    if pc < RISK_THRESHOLDS["medium_max"]:
        return "MEDIUM"
    if pc < RISK_THRESHOLDS["high_max"]:
        return "HIGH"
    return "CRITICAL"


def sigma_from_uncertainty_scale(
    uncertainty_scale: float,
    base_sigma_km: float = BASE_SIGMA_KM,
) -> float:
    """Convert guide's dimensionless uncertainty_scale to assumed sigma."""
    if not isfinite(float(uncertainty_scale)) or uncertainty_scale <= 0:
        raise ValueError("uncertainty_scale must be finite and positive.")
    if not isfinite(float(base_sigma_km)) or base_sigma_km <= 0:
        raise ValueError("base_sigma_km must be finite and positive.")
    return float(base_sigma_km * uncertainty_scale)


def assess_conjunction(
    conjunction: dict,
    combined_radius_km: float = DEFAULT_COMBINED_RADIUS_KM,
    base_sigma_km: float = BASE_SIGMA_KM,
) -> dict:
    """Create the exact Risk Assessment structure from guide Section 5.2."""
    required = ("conjunction_id", "miss_distance_km", "data_quality")
    missing = [key for key in required if key not in conjunction]
    if missing:
        raise KeyError(f"Conjunction missing required fields: {missing}")

    dq = conjunction["data_quality"]
    if "uncertainty_scale" not in dq:
        raise KeyError("data_quality.uncertainty_scale is required")

    sigma = sigma_from_uncertainty_scale(dq["uncertainty_scale"], base_sigma_km)
    pc = calculate_pc_2d(
        miss_distance_km=float(conjunction["miss_distance_km"]),
        combined_radius_km=combined_radius_km,
        sigma_km=sigma,
    )

    ages = [
        dq.get("tle_age_a_h"),
        dq.get("tle_age_b_h"),
    ]
    old = [
        f"Object {'A' if i == 0 else 'B'} TLE is {age:g}h old"
        for i, age in enumerate(ages)
        if age is not None and age > 72.0
    ]
    notes = "; ".join(old) if old else (
        "2D isotropic Gaussian estimate; uncertainty derived from configured "
        "base sigma and Member 1 uncertainty_scale"
    )

    return {
        "conjunction_id": conjunction["conjunction_id"],
        "pc": pc,
        "risk_level": classify_risk(pc),
        "anomaly_flag": bool(old),
        "notes": notes,
    }
