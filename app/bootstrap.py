from app.application.use_cases.submit_payment import SubmitPaymentUseCase
from app.infrastructure.clients.payment_request_service import (
    HttpPaymentRequestGateway,
)
from app.infrastructure.settings import settings
from app.infrastructure.security.access_policy import (
    FixedWindowRateLimiter,
    GatewayAccessPolicy,
)

payment_request_gateway = HttpPaymentRequestGateway(settings)
rate_limiter = FixedWindowRateLimiter(
    request_limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)
gateway_access_policy = GatewayAccessPolicy(settings, rate_limiter)


def get_payment_request_gateway() -> HttpPaymentRequestGateway:
    return payment_request_gateway


def get_submit_payment_use_case() -> SubmitPaymentUseCase:
    gateway = get_payment_request_gateway()
    return SubmitPaymentUseCase(payment_request_gateway=gateway)


def get_gateway_access_policy() -> GatewayAccessPolicy:
    return gateway_access_policy
