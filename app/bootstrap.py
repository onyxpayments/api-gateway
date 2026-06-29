from app.application.use_cases.submit_payment import SubmitPaymentUseCase
from app.infrastructure.clients.payment_request_service import (
    HttpPaymentRequestGateway,
)
from app.infrastructure.settings import settings

payment_request_gateway = HttpPaymentRequestGateway(settings)


def get_payment_request_gateway() -> HttpPaymentRequestGateway:
    return payment_request_gateway


def get_submit_payment_use_case() -> SubmitPaymentUseCase:
    gateway = get_payment_request_gateway()
    return SubmitPaymentUseCase(payment_request_gateway=gateway)
