"""Application configuration settings."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment or defaults."""

    # WhatsApp Cloud API Settings
    WHATSAPP_VERIFY_TOKEN: str = "whatsapp_print_agent_verify_token_123"
    WHATSAPP_API_TOKEN: str = "mock_access_token_here"
    WHATSAPP_PHONE_NUMBER_ID: str = "mock_phone_number_id_here"
    WHATSAPP_GRAPH_API_URL: str = "https://graph.facebook.com/v19.0"

    # Database & Storage
    DATABASE_URL: str = "sqlite:///./print_agent.db"
    STORAGE_DIR: str = "./storage/uploads"
    OUTPUT_DIR: str = "./output"

    # Environment & Simulation
    APP_ENV: str = "development"
    MOCK_MODE: bool = True

    # Pricing Defaults (in INR)
    BW_RATE_PER_PAGE: float = 2.0
    COLOR_RATE_PER_PAGE: float = 10.0

    # Razorpay Payment Gateway Settings
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""
    PAYMENT_GATEWAY_PROVIDER: str = "razorpay"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_storage_path(self) -> Path:
        """Ensure and return the storage directory Path."""
        path = Path(self.STORAGE_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def get_output_path(self) -> Path:
        """Ensure and return the output directory Path."""
        path = Path(self.OUTPUT_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()


def reload_settings() -> Settings:
    """Reload settings from .env file into the existing singleton in-place."""
    new_settings = Settings()
    for field_name in new_settings.model_fields:
        setattr(settings, field_name, getattr(new_settings, field_name))
    return settings
