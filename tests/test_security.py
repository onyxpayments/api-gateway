import pytest
from fastapi import HTTPException

from app.infrastructure.security.access_policy import (
    FixedWindowRateLimiter,
    GatewayAccessPolicy,
)
from app.infrastructure.settings import Settings


def create_settings(**overrides):
    values = {
        "api_basic_auth_enabled": True,
        "api_basic_auth_username": "merchant",
        "api_basic_auth_secret": "secret-key",
        "rate_limit_enabled": True,
        "rate_limit_requests": 2,
        "rate_limit_window_seconds": 60,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_basic_auth_rejects_invalid_secret():
    policy = GatewayAccessPolicy(
        create_settings(rate_limit_enabled=False),
        FixedWindowRateLimiter(2, 60),
    )

    with pytest.raises(HTTPException) as captured:
        policy.enforce("merchant", "wrong", "127.0.0.1")

    assert captured.value.status_code == 401


def test_rate_limit_is_scoped_to_authenticated_username():
    current_time = [100.0]
    limiter = FixedWindowRateLimiter(
        request_limit=2,
        window_seconds=60,
        clock=lambda: current_time[0],
    )
    policy = GatewayAccessPolicy(create_settings(), limiter)

    policy.enforce("merchant", "secret-key", "127.0.0.1")
    policy.enforce("merchant", "secret-key", "127.0.0.2")

    with pytest.raises(HTTPException) as captured:
        policy.enforce("merchant", "secret-key", "127.0.0.3")

    assert captured.value.status_code == 429
    assert captured.value.headers["Retry-After"] == "60"

    current_time[0] = 161.0
    policy.enforce("merchant", "secret-key", "127.0.0.3")


def test_basic_auth_configuration_requires_both_credentials():
    with pytest.raises(ValueError):
        Settings(
            _env_file=None,
            api_basic_auth_enabled=True,
            api_basic_auth_username="merchant",
            api_basic_auth_secret="",
        )
