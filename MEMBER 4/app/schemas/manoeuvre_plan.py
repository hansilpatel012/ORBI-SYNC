import math
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ManoeuvrePlanBase(BaseModel):
    """Base schema for collision avoidance manoeuvre plans matching public.manoeuvre_plans."""

    satellite_id: UUID = Field(
        ...,
        description="UUID of the maneuvering satellite (FK to satellites.id)",
        examples=["a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"],
    )
    conjunction_id: Optional[UUID] = Field(
        default=None,
        description="Optional UUID of the conjunction event being mitigated (FK to conjunction_events.id)",
        examples=["c2ffcd99-9d0b-4fe8-bb6d-6bb9bd380c33"],
    )
    delta_v: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Magnitude of velocity change impulse in meters per second (m/s) or km/s",
        examples=[1.25],
    )
    fuel_estimate: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Estimated fuel / propellant consumption in kilograms (kg)",
        examples=[0.48],
    )
    proposed_time: Optional[datetime] = Field(
        default=None,
        description="Planned ignition or execution time in UTC (ISO-8601)",
        examples=["2026-11-25T12:00:00Z"],
    )
    status: Optional[str] = Field(
        default="proposed",
        max_length=50,
        description="Manoeuvre status (e.g. proposed, approved, executing, completed, cancelled, rejected)",
        examples=["proposed"],
    )

    @field_validator("delta_v", "fuel_estimate", mode="after")
    @classmethod
    def validate_finite_numbers(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise ValueError("Numeric metrics must be finite numbers and not NaN or Infinity.")
        return v


class ManoeuvrePlanCreate(ManoeuvrePlanBase):
    """Payload for creating a new manoeuvre plan."""

    pass


class ManoeuvrePlanUpdate(BaseModel):
    """Payload for updating an existing manoeuvre plan. At least one field must be provided."""

    conjunction_id: Optional[UUID] = Field(
        default=None,
        description="Updated conjunction event reference",
    )
    delta_v: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Updated delta_v magnitude",
    )
    fuel_estimate: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Updated fuel estimate in kg",
    )
    proposed_time: Optional[datetime] = Field(
        default=None,
        description="Updated proposed execution time",
    )
    status: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Updated manoeuvre status (e.g. approved, executing, completed, cancelled)",
    )

    @field_validator("delta_v", "fuel_estimate", mode="after")
    @classmethod
    def validate_finite_numbers(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise ValueError("Numeric metrics must be finite numbers and not NaN or Infinity.")
        return v

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "ManoeuvrePlanUpdate":
        if (
            self.conjunction_id is None
            and self.delta_v is None
            and self.fuel_estimate is None
            and self.proposed_time is None
            and self.status is None
        ):
            raise ValueError("At least one field must be provided for update.")
        return self


class ManoeuvrePlanResponse(ManoeuvrePlanBase):
    """Manoeuvre plan record returned to clients."""

    id: UUID = Field(..., description="Unique manoeuvre plan UUID")
    created_at: datetime = Field(..., description="Timestamp when plan was generated")

    model_config = ConfigDict(from_attributes=True)


class ManoeuvrePlanPagination(BaseModel):
    """Paginated response containing manoeuvre plans and pagination metadata."""

    items: List[ManoeuvrePlanResponse] = Field(
        ..., description="List of matching manoeuvre plans"
    )
    total: int = Field(..., ge=0, description="Total number of matching manoeuvre plans")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of available pages")
