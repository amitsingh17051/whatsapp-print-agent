"""Schemas for print jobs."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.pricing import PrintOptions


class PrintJobCreate(BaseModel):
    """Schema to create a print job."""

    customer_phone: str
    document_id: str
    options: PrintOptions
    total_price: float = Field(..., ge=0)


class PrintJobResponse(BaseModel):
    """Schema for print job details."""

    id: str
    customer_id: str
    document_id: str
    copies: int
    color: str
    duplex: str
    paper_size: str
    total_price: float
    status: Literal["created", "queued", "printing", "completed", "failed"]
    pickup_code: str | None = None
    created_at: datetime
    updated_at: datetime
