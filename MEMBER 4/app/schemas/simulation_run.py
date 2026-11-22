from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SimulationRunBase(BaseModel):
    """Base schema for simulation runs matching public.simulation_runs."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Name or title identifying the simulation run",
        examples=["LEO-Monte-Carlo-Conjunction-Batch-04"],
    )
    status: str = Field(
        default="pending",
        max_length=50,
        description="Execution state (e.g. pending, running, completed, failed, cancelled)",
        examples=["pending"],
    )
    input_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Arbitrary input parameters, time horizon, step size, and initial conditions in JSONB",
        examples=[{
            "step_size_seconds": 60,
            "duration_hours": 72,
            "satellites": ["a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"],
            "propagation_model": "SGP4"
        }],
    )
    result_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Simulation outputs, collision risks, execution metrics, and completion timestamps in JSONB",
        examples=[{
            "conjunctions_detected": 1,
            "minimum_miss_distance_km": 0.45,
            "completed_at": "2026-11-22T03:00:00Z",
            "execution_time_seconds": 14.2
        }],
    )


class SimulationRunCreate(SimulationRunBase):
    """Payload for registering a new simulation run."""

    pass


class SimulationRunUpdate(BaseModel):
    """Payload for updating a simulation run's status, input parameters, or results."""

    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Updated simulation title",
    )
    status: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Updated execution status (e.g. running, completed, failed)",
    )
    input_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated simulation input parameters",
    )
    result_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated simulation output data, metrics, or error logs",
    )

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "SimulationRunUpdate":
        if (
            self.name is None
            and self.status is None
            and self.input_data is None
            and self.result_data is None
        ):
            raise ValueError("At least one field must be provided for update.")
        return self


class SimulationRunResponse(SimulationRunBase):
    """Simulation run record representation returned to clients."""

    id: UUID = Field(..., description="Unique simulation run UUID")
    created_at: datetime = Field(..., description="Timestamp when the simulation was created")

    model_config = ConfigDict(from_attributes=True)


class SimulationRunPagination(BaseModel):
    """Paginated response containing simulation run records and pagination metadata."""

    items: List[SimulationRunResponse] = Field(
        ..., description="List of matching simulation runs"
    )
    total: int = Field(..., ge=0, description="Total number of matching simulation runs")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of available pages")
