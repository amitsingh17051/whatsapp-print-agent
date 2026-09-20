"""Schemas for payments."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    """Schema to initiate a payment."""

    print_job_id: str
    amount: float = Field(..., gt=0)


class PaymentVerify(BaseModel):
    """Schema to verify a test payment."""

    payment_id: str
    mock_confirm: bool = True


class PaymentResponse(BaseModel):
    """Schema for payment details."""

    id: str
    print_job_id: str
    amount: float
    status: Literal["pending", "completed", "failed"]
    payment_method: str
    created_at: datetime
    verified_at: datetime | None = None
