import math
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OrbitalStateBase(BaseModel):
    """Base orbital state attributes conforming to the public.orbital_states schema."""

    satellite_id: UUID = Field(
        ...,
        description="UUID foreign key referencing the associated satellite in public.satellites",
        examples=["a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"],
    )
    epoch: datetime = Field(
        ...,
        description="Observation or propagation epoch in UTC (ISO-8601)",
        examples=["2026-11-22T02:30:00Z"],
    )
    position_x: Optional[float] = Field(
        default=None,
        description="Position X coordinate in kilometers (km) in TEME/ECI coordinate frame",
        examples=[6871.5],
    )
    position_y: Optional[float] = Field(
        default=None,
        description="Position Y coordinate in kilometers (km) in TEME/ECI coordinate frame",
        examples=[-1200.3],
    )
    position_z: Optional[float] = Field(
        default=None,
        description="Position Z coordinate in kilometers (km) in TEME/ECI coordinate frame",
        examples=[340.1],
    )
    velocity_x: Optional[float] = Field(
        default=None,
        description="Velocity X component in kilometers per second (km/s) in TEME/ECI coordinate frame",
        examples=[0.85],
    )
    velocity_y: Optional[float] = Field(
        default=None,
        description="Velocity Y component in kilometers per second (km/s) in TEME/ECI coordinate frame",
        examples=[7.45],
    )
    velocity_z: Optional[float] = Field(
        default=None,
        description="Velocity Z component in kilometers per second (km/s) in TEME/ECI coordinate frame",
        examples=[1.82],
    )
    tle_line1: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Raw TLE Line 1 used for SGP4 propagation (optional)",
        examples=["1 25544U 98067A   26325.50000000  .00016717  00000-0  10270-3 0  9001"],
    )
    tle_line2: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Raw TLE Line 2 used for SGP4 propagation (optional)",
        examples=["2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.72125391563537"],
    )

    @field_validator(
        "position_x",
        "position_y",
        "position_z",
        "velocity_x",
        "velocity_y",
        "velocity_z",
        mode="after",
    )
    @classmethod
    def validate_finite_numbers(cls, v: Optional[float]) -> Optional[float]:
        """Ensure numerical values are finite and not NaN or Infinity."""
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise ValueError("Orbital state position and velocity values must be finite numbers.")
        return v


class OrbitalStateCreate(OrbitalStateBase):
    """Payload for submitting an orbital state vector from the SGP4 propagation module."""

    pass


class OrbitalStateResponse(OrbitalStateBase):
    """Orbital state record representation returned to clients."""

    id: UUID = Field(..., description="Unique orbital state UUID")
    created_at: datetime = Field(..., description="Timestamp when the state record was stored")

    model_config = ConfigDict(from_attributes=True)


class OrbitalStatePagination(BaseModel):
    """Paginated response containing orbital state records and metadata."""

    items: List[OrbitalStateResponse] = Field(..., description="List of orbital state records")
    total: int = Field(..., ge=0, description="Total number of matching orbital state records")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of available pages")
