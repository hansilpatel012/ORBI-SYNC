import math
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SustainabilityMetricBase(BaseModel):
    """Base schema for sustainability metrics matching public.sustainability_metrics."""

    simulation_id: Optional[UUID] = Field(
        default=None,
        description="UUID of the associated simulation run (FK to simulation_runs.id)",
        examples=["b2ffcd88-8d0a-4fe7-aa5c-5aa8ac270b22"],
    )
    total_delta_v: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Total velocity change (delta-v) expended across avoidance maneuvers in m/s or km/s",
        examples=[4.85],
    )
    estimated_fuel_saved: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Estimated propellant mass saved via optimized trajectories in kilograms (kg)",
        examples=[1.72],
    )
    avoided_close_approaches: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total count of critical close-approach conjunctions successfully mitigated",
        examples=[3],
    )

    @field_validator("total_delta_v", "estimated_fuel_saved", mode="after")
    @classmethod
    def validate_finite_numbers(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise ValueError("Numerical sustainability metrics must be finite numbers and not NaN or Infinity.")
        return v


class SustainabilityMetricCreate(SustainabilityMetricBase):
    """Payload for creating a new sustainability metric entry."""

    pass


class SustainabilityMetricUpdate(BaseModel):
    """Payload for updating an existing sustainability metric. At least one field must be provided."""

    simulation_id: Optional[UUID] = Field(
        default=None,
        description="Updated simulation run reference",
    )
    total_delta_v: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Updated total delta-v expenditure",
    )
    estimated_fuel_saved: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Updated estimated propellant saved in kg",
    )
    avoided_close_approaches: Optional[int] = Field(
        default=None,
        ge=0,
        description="Updated count of avoided close approaches",
    )

    @field_validator("total_delta_v", "estimated_fuel_saved", mode="after")
    @classmethod
    def validate_finite_numbers(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (math.isnan(v) or math.isinf(v)):
            raise ValueError("Numerical sustainability metrics must be finite numbers and not NaN or Infinity.")
        return v

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "SustainabilityMetricUpdate":
        if (
            self.simulation_id is None
            and self.total_delta_v is None
            and self.estimated_fuel_saved is None
            and self.avoided_close_approaches is None
        ):
            raise ValueError("At least one field must be provided for update.")
        return self


class SustainabilityMetricResponse(SustainabilityMetricBase):
    """Sustainability metric record representation returned to clients."""

    id: UUID = Field(..., description="Unique sustainability metric UUID")
    created_at: datetime = Field(..., description="Timestamp when metric was computed and logged")

    model_config = ConfigDict(from_attributes=True)


class SustainabilityMetricPagination(BaseModel):
    """Paginated response containing sustainability metric records and metadata."""

    items: List[SustainabilityMetricResponse] = Field(
        ..., description="List of matching sustainability metric records"
    )
    total: int = Field(..., ge=0, description="Total number of matching records")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of available pages")
