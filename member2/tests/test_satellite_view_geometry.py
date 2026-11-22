import math
import pytest
from satellite_view_geometry import satellite_relative_geometry, risk_display_color


def test_target_along_track_has_zero_azimuth_and_elevation():
    result = satellite_relative_geometry(
        [7000, 0, 0], [0, 7.5, 0],
        [7000, 10, 0], [0, 7.5, 0],
    )
    assert result["range_km"] == pytest.approx(10)
    assert result["azimuth_deg_from_along_track_toward_cross_track"] == pytest.approx(0)
    assert result["elevation_deg_from_orbital_plane_toward_radial"] == pytest.approx(0)


def test_target_cross_track_has_90_degree_azimuth():
    result = satellite_relative_geometry(
        [7000, 0, 0], [0, 7.5, 0],
        [7000, 0, 10], [0, 7.5, 0],
    )
    assert result["azimuth_deg_from_along_track_toward_cross_track"] == pytest.approx(90)


def test_approaching_target_has_positive_closing_speed():
    result = satellite_relative_geometry(
        [7000, 0, 0], [0, 7.5, 0],
        [7000, 10, 0], [0, 6.5, 0],
    )
    assert result["closing_speed_kms"] > 0
    assert result["motion_status"] == "APPROACHING"


def test_invalid_zero_orbit_normal_rejected():
    with pytest.raises(ValueError):
        satellite_relative_geometry([7000,0,0], [1,0,0], [7001,0,0], [1,0,0])


def test_risk_colors():
    assert risk_display_color("LOW") == "green"
    assert risk_display_color("HIGH") == "orange"
    assert risk_display_color("CRITICAL") == "red"
