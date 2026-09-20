"""Schemas for print options and pricing calculations."""

from typing import Literal

from pydantic import BaseModel, Field


class PrintOptions(BaseModel):
    """User specified print options."""

    copies: int = Field(default=1, ge=1, le=50, description="Number of copies (1 to 50)")
    color: Literal["bw", "color"] = Field(default="bw", description="Print color: 'bw' or 'color'")
    duplex: Literal["single", "double"] = Field(default="single", description="Duplex mode: 'single' or 'double'")
    paper_size: Literal["A4"] = Field(default="A4", description="Paper size (A4 only in MVP)")


class PricingCalculationRequest(BaseModel):
    """Request model for pricing calculation."""

    page_count: int = Field(..., ge=1, description="Total number of document pages")
    options: PrintOptions = Field(default_factory=PrintOptions)


class PricingCalculationResponse(BaseModel):
    """Response model for pricing calculation."""

    page_count: int
    copies: int
    color: str
    duplex: str
    paper_size: str
    rate_per_page: float
    total_price: float
    currency: str = "INR"
