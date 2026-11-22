"""Satellite-relative geometry for the ORBI-SYNC onboard view.

Inputs must be simultaneous inertial position/velocity vectors in a common
frame (e.g. TEME or GCRF), with positions in km and velocities in km/s.
The axes used here are:
  R: radial outward from Earth
  T: along-track, direction of satellite motion
  N: orbit normal / cross-track

Azimuth is measured from +T toward +N. Elevation is measured from the
local orbital plane toward +R. This is a geometric display calculation,
not a collision-probability calculation or an operational sensor solution.
"""
from __future__ import annotations
import math


def _vec3(name, value):
    if len(value) != 3:
        raise ValueError(f"{name} must contain exactly 3 values")
    result = tuple(float(x) for x in value)
    if not all(math.isfinite(x) for x in result):
        raise ValueError(f"{name} must contain finite values")
    return result


def _dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def _cross(a, b):
    return (
        a[1]*b[2] - a[2]*b[1],
        a[2]*b[0] - a[0]*b[2],
        a[0]*b[1] - a[1]*b[0],
    )


def _scale(v, k):
    return tuple(x*k for x in v)


def _sub(a, b):
    return tuple(x-y for x, y in zip(a, b))


def _norm(v):
    return math.sqrt(_dot(v, v))


def satellite_relative_geometry(
    satellite_position_km,
    satellite_velocity_kms,
    target_position_km,
    target_velocity_kms,
):
    """Calculate target's range, RTN components, azimuth/elevation and motion."""
    r_sat = _vec3("satellite_position_km", satellite_position_km)
    v_sat = _vec3("satellite_velocity_kms", satellite_velocity_kms)
    r_obj = _vec3("target_position_km", target_position_km)
    v_obj = _vec3("target_velocity_kms", target_velocity_kms)

    r_mag = _norm(r_sat)
    h = _cross(r_sat, v_sat)
    h_mag = _norm(h)
    if r_mag == 0 or h_mag == 0:
        raise ValueError("Satellite position and angular momentum must be non-zero")

    R = _scale(r_sat, 1.0 / r_mag)
    N = _scale(h, 1.0 / h_mag)
    T = _cross(N, R)

    relative_r = _sub(r_obj, r_sat)
    relative_v = _sub(v_obj, v_sat)

    rtn = (_dot(relative_r, R), _dot(relative_r, T), _dot(relative_r, N))
    range_km = _norm(relative_r)
    if range_km == 0:
        raise ValueError("Target and satellite positions are identical")

    radial, along, cross_track = rtn
    azimuth = math.degrees(math.atan2(cross_track, along))
    if azimuth < 0:
        azimuth += 360.0
    elevation = math.degrees(
        math.atan2(radial, math.hypot(along, cross_track))
    )
    range_rate = _dot(relative_r, relative_v) / range_km
    closing_speed = -range_rate

    # Constant-relative-velocity estimate only; not a substitute for SGP4 TCA.
    t_cpa_linear = -_dot(relative_r, relative_v) / _dot(relative_v, relative_v) \
        if _dot(relative_v, relative_v) > 0 else None

    return {
        "range_km": range_km,
        "relative_position_rtn_km": {
            "radial_R_km": radial,
            "along_track_T_km": along,
            "cross_track_N_km": cross_track,
        },
        "azimuth_deg_from_along_track_toward_cross_track": azimuth,
        "elevation_deg_from_orbital_plane_toward_radial": elevation,
        "range_rate_kms": range_rate,
        "closing_speed_kms": closing_speed,
        "motion_status": "APPROACHING" if closing_speed > 0 else (
            "RECEDING" if closing_speed < 0 else "NEAR_ZERO_RANGE_RATE"
        ),
        "linear_constant_velocity_cpa_seconds": t_cpa_linear,
        "warning": (
            "Display geometry only. Use Member 1's propagated trajectories and "
            "refined TCA for operational timing; this linear estimate is approximate."
        ),
    }


def risk_display_color(risk_level: str) -> str:
    """Map the existing risk label to a UI colour name."""
    colors = {
        "LOW": "green",
        "MEDIUM": "yellow",
        "HIGH": "orange",
        "CRITICAL": "red",
    }
    try:
        return colors[risk_level.upper()]
    except (AttributeError, KeyError):
        return "grey"
