import hashlib
import logging
import secrets
import threading
import time
from dataclasses import dataclass
from math import ceil
from typing import Callable

from fastapi import HTTPException, status

from app.infrastructure.settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitWindow:
    count: int
    resets_at: float


class FixedWindowRateLimiter:
    def __init__(
        self,
        request_limit: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.request_limit = request_limit
        self.window_seconds = window_seconds
        self.clock = clock
        self.windows: dict[str, RateLimitWindow] = {}
        self.lock = threading.Lock()

    def retry_after(self, subject: str) -> int | None:
        now = self.clock()
        with self.lock:
            window = self.windows.get(subject)
            if window is None or now >= window.resets_at:
                self.windows[subject] = RateLimitWindow(
                    count=1,
                    resets_at=now + self.window_seconds,
                )
                return None

            if window.count >= self.request_limit:
                return max(1, ceil(window.resets_at - now))

            window.count += 1
            return None


class GatewayAccessPolicy:
    def __init__(
        self,
        settings: Settings,
        rate_limiter: FixedWindowRateLimiter,
    ):
        self.settings = settings
        self.rate_limiter = rate_limiter

    def enforce(
        self,
        username: str | None,
        secret: str | None,
        client_id: str,
    ) -> None:
        subject = client_id
        if self.settings.api_basic_auth_enabled:
            if not self._valid_credentials(username, secret):
                logger.warning(
                    "basic_auth_rejected",
                    extra={"client_id": client_id},
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or missing Basic credentials",
                    headers={"WWW-Authenticate": "Basic"},
                )
            subject = self._anonymous_subject(username or "")

        if not self.settings.rate_limit_enabled:
            return

        retry_after = self.rate_limiter.retry_after(subject)
        if retry_after is not None:
            logger.warning(
                "rate_limit_exceeded",
                extra={
                    "client_id": client_id,
                    "rate_limit_subject": subject,
                    "retry_after_seconds": retry_after,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(retry_after)},
            )

    def _valid_credentials(
        self,
        username: str | None,
        secret: str | None,
    ) -> bool:
        if username is None or secret is None:
            return False
        username_matches = secrets.compare_digest(
            username,
            self.settings.api_basic_auth_username,
        )
        secret_matches = secrets.compare_digest(
            secret,
            self.settings.api_basic_auth_secret,
        )
        return username_matches and secret_matches

    @staticmethod
    def _anonymous_subject(username: str) -> str:
        digest = hashlib.sha256(username.encode()).hexdigest()[:16]
        return f"basic:{digest}"
