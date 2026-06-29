from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "api-gateway"
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
    api_basic_auth_enabled: bool = False
    api_basic_auth_username: str = ""
    api_basic_auth_secret: str = ""
    rate_limit_enabled: bool = True
    rate_limit_requests: int = Field(default=60, ge=1)
    rate_limit_window_seconds: int = Field(default=60, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_basic_auth_credentials(self):
        if self.api_basic_auth_enabled and (
            not self.api_basic_auth_username or not self.api_basic_auth_secret
        ):
            raise ValueError("Basic authentication requires a username and secret")
        return self


settings = Settings()
