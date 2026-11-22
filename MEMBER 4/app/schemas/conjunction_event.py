import math
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConjunctionEventBase(BaseModel):
    """Base schema for conjunction / collision events matching public.conjunction_events."""

    satellite_1_id: UUID = Field(
        ...,
        description="UUID of the primary satellite (FK to satellites.id)",
        examples=["a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"],
    )
    satellite_2_id: UUID = Field(
        ...,
        description="UUID of the secondary satellite, target, or debris (FK to satellites.id)",
        examples=["b1ffcd88-8d0a-4fe7-aa5c-5aa8ac270b22"],
    )
    closest_approach: Optional[datetime] = Field(
        default=None,
        description="Time of Closest Approach (TCA) in UTC (ISO-8601)",
        examples=["2026-11-25T14:45:00Z"],
    )
    miss_distance_km: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Predicted minimum miss distance in kilometers (km)",
        examples=[0.42],
    )
    collision_probability: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Calculated probability of collision (between 0.0 and 1.0)",
        examples=[0.00125],
    )
    risk_level: Optional[str] = Field(
        default="unknown",
        max_length=50,
        description="Assessed risk tier (e.g. low, medium, high, critical, unknown)",
        examples=["high"],
    )
    status: Optional[str] = Field(
        default="detected",
        max_length=50,
        description="Event resolution state (e.g. detected, monitoring, mitigated, resolved, dismissed)",
        examples=["detected"],
    )

    @field_validator("miss_distance_km", "collision_probability", mode="after")
    @classmethod
    def validate_finite_numbers(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise ValueError("Numeric values must be finite and not NaN or Infinity.")
        return v

    @model_validator(mode="after")
    def validate_distinct_satellites(self) -> "ConjunctionEventBase":
        if self.satellite_1_id == self.satellite_2_id:
            raise ValueError("satellite_1_id and satellite_2_id must be distinct satellites.")
        return self


class ConjunctionEventCreate(ConjunctionEventBase):
    """Payload for registering a newly predicted conjunction event."""

    pass


class ConjunctionEventResponse(ConjunctionEventBase):
    """Conjunction event record representation returned to clients."""

    id: UUID = Field(..., description="Unique conjunction event UUID")
    created_at: datetime = Field(..., description="Timestamp when event was logged")

    model_config = ConfigDict(from_attributes=True)


class ConjunctionEventPagination(BaseModel):
    """Paginated response containing conjunction events and pagination metadata."""

    items: List[ConjunctionEventResponse] = Field(
        ..., description="List of matching conjunction events"
    )
    total: int = Field(..., ge=0, description="Total number of matching conjunction events")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of available pages")
