from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SatelliteBase(BaseModel):
    """Base satellite attributes."""

    norad_id: int = Field(
        ...,
        ge=1,
        le=999999,
        description="Unique NORAD Satellite Catalog Number (positive integer)",
        examples=[25544],
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Satellite name or designation",
        examples=["ISS (ZARYA)"],
    )
    operator_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Name of the satellite operating agency or enterprise",
        examples=["NASA / International"],
    )
    status: str = Field(
        default="ACTIVE",
        min_length=1,
        max_length=50,
        description="Operational status (e.g., ACTIVE, INACTIVE, DECAYED, DEORBITED)",
        examples=["ACTIVE"],
    )


class SatelliteCreate(SatelliteBase):
    """Payload for registering a new satellite."""

    pass


class SatelliteUpdate(BaseModel):
    """Payload for updating an existing satellite. At least one field must be provided."""

    norad_id: Optional[int] = Field(
        default=None,
        ge=1,
        le=999999,
        description="Updated NORAD Catalog Number",
    )
    name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated satellite name",
    )
    operator_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated operator name",
    )
    status: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Updated status (e.g., ACTIVE, INACTIVE, DECAYED)",
    )

    @model_validator(mode="after")
    def check_at_least_one_field(self) -> "SatelliteUpdate":
        if (
            self.norad_id is None
            and self.name is None
            and self.operator_name is None
            and self.status is None
        ):
            raise ValueError("At least one field must be provided for update.")
        return self


class SatelliteResponse(BaseModel):
    """Satellite representation returned to clients."""

    id: UUID = Field(..., description="Unique satellite UUID")
    norad_id: int = Field(..., description="NORAD Catalog Number")
    name: str = Field(..., description="Satellite name")
    operator_name: str = Field(..., description="Operator name")
    status: str = Field(..., description="Operational status")
    created_at: datetime = Field(..., description="Record creation timestamp")

    model_config = ConfigDict(from_attributes=True)


class SatellitePagination(BaseModel):
    """Paginated response containing satellite records and metadata."""

    items: List[SatelliteResponse] = Field(..., description="List of satellite records")
    total: int = Field(..., ge=0, description="Total number of matching satellites")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of available pages")
