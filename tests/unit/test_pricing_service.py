"""Unit tests for PricingService."""

import pytest

from app.schemas.pricing import PrintOptions
from app.services.pricing import PricingService


def test_black_and_white_pricing():
    """Verify B&W rate of ₹2.00 per page."""
    options = PrintOptions(copies=1, color="bw")
    result = PricingService.calculate_price(page_count=5, options=options)

    assert result.rate_per_page == 2.0
    assert result.total_price == 10.0  # 5 * 1 * 2.0
    assert result.currency == "INR"


def test_color_pricing():
    """Verify Color rate of ₹10.00 per page."""
    options = PrintOptions(copies=2, color="color")
    result = PricingService.calculate_price(page_count=10, options=options)

    assert result.rate_per_page == 10.0
    assert result.total_price == 200.0  # 10 * 2 * 10.0


def test_multiple_copies_calculation():
    """Verify calculation across copies and duplex."""
    options = PrintOptions(copies=3, color="bw", duplex="double")
    result = PricingService.calculate_price(page_count=3, options=options)

    assert result.total_price == 18.0  # 3 * 3 * 2.0


def test_invalid_page_count_raises_error():
    """Verify zero or negative page count is rejected."""
    options = PrintOptions(copies=1, color="bw")
    with pytest.raises(ValueError, match="Page count must be at least 1"):
        PricingService.calculate_price(page_count=0, options=options)


def test_invalid_copies_count_raises_error():
    """Verify copy count limits are enforced."""
    with pytest.raises(ValueError):
        # Pydantic validation error or service check
        options = PrintOptions.model_construct(copies=0, color="bw", duplex="single", paper_size="A4")
        PricingService.calculate_price(page_count=5, options=options)
