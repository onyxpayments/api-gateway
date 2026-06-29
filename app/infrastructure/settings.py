from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    payment_request_service_url: str = Field(
        default="http://payment-request-service:8003"
    )
    payment_request_timeout_seconds: float = Field(
        default=10,
        gt=0,
    )
    payment_request_health_timeout_seconds: float = Field(
        default=2,
        gt=0,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
