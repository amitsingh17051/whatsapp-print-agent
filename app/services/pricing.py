"""Pricing service for deterministic print cost calculation."""

from app.config import settings
from app.schemas.pricing import PricingCalculationResponse, PrintOptions


class PricingService:
    """Deterministic pricing calculator based on knowledge/pricing.md."""

    @classmethod
    def get_rate_per_page(cls, color_mode: str) -> float:
        """Return unit price per page based on color mode."""
        if color_mode == "color":
            return settings.COLOR_RATE_PER_PAGE
        return settings.BW_RATE_PER_PAGE

    @classmethod
    def calculate_price(
        cls,
        page_count: int,
        options: PrintOptions,
    ) -> PricingCalculationResponse:
        """
        Calculate the total print price deterministically.

        Formula: Total Price = Page Count * Number of Copies * Rate per Page
        """
        if page_count < 1:
            raise ValueError("Page count must be at least 1.")
        if options.copies < 1:
            raise ValueError("Number of copies must be at least 1.")
        if options.copies > 50:
            raise ValueError("Maximum 50 copies allowed per job.")

        rate = cls.get_rate_per_page(options.color)
        total_price = round(page_count * options.copies * rate, 2)

        return PricingCalculationResponse(
            page_count=page_count,
            copies=options.copies,
            color=options.color,
            duplex=options.duplex,
            paper_size=options.paper_size,
            rate_per_page=rate,
            total_price=total_price,
            currency="INR",
        )
