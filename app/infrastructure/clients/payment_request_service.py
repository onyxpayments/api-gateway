import logging

import httpx
from pydantic import BaseModel, ValidationError
from uuid import UUID

from app.application.commands import SubmitPaymentCommand
from app.application.exceptions import (
    InvalidPaymentRequestResponse,
    PaymentRequestRejected,
    PaymentRequestUnavailable,
)
from app.application.results import PaymentSubmissionResult
from app.infrastructure.settings import Settings
from app.infrastructure.observability.context import (
    CORRELATION_ID_HEADER,
    get_correlation_id,
)

logger = logging.getLogger(__name__)


class PaymentRequestServiceResponse(BaseModel):
    transaction_id: UUID
    status: str
    message: str | None = None


class HttpPaymentRequestGateway:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def submit(
        self,
        command: SubmitPaymentCommand,
    ) -> PaymentSubmissionResult:
        base_url = self.settings.payment_request_service_url.rstrip("/")
        url = f"{base_url}/payments"
        payload = {
            "transaction_id": str(command.payment_id),
            "amount": str(command.amount),
            "currency": command.currency,
            "notification_url": command.notification_url,
            "customer": {
                "first_name": command.customer.first_name,
                "last_name": command.customer.last_name,
                "personal_id": command.customer.personal_id,
            },
        }
        correlation_id = get_correlation_id()
        headers = {CORRELATION_ID_HEADER: correlation_id} if correlation_id else {}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.settings.payment_request_timeout_seconds,
                )
        except httpx.RequestError as error:
            logger.warning(
                "payment_request_service_unavailable",
                extra={"payment_id": str(command.payment_id)},
            )
            raise PaymentRequestUnavailable(
                "Could not reach payment request service"
            ) from error

        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            logger.warning(
                "payment_request_service_rejected_request",
                extra={
                    "payment_id": str(command.payment_id),
                    "upstream_status": response.status_code,
                },
            )
            raise PaymentRequestRejected(response.status_code, detail)

        try:
            response_body = response.json()
            validate = PaymentRequestServiceResponse.model_validate
            upstream = validate(response_body)
        except (ValueError, ValidationError) as error:
            logger.error(
                "payment_request_service_invalid_response",
                extra={
                    "payment_id": str(command.payment_id),
                    "upstream_status": response.status_code,
                },
            )
            raise InvalidPaymentRequestResponse(
                "Payment request service returned an invalid response"
            ) from error

        logger.info(
            "payment_request_forwarded",
            extra={
                "payment_id": str(command.payment_id),
                "upstream_status": response.status_code,
            },
        )
        return PaymentSubmissionResult(
            payment_id=upstream.transaction_id,
            status=upstream.status,
            message=upstream.message,
        )

    async def is_ready(self) -> bool:
        base_url = self.settings.payment_request_service_url.rstrip("/")
        url = f"{base_url}/health/ready"
        try:
            async with httpx.AsyncClient() as client:
                timeout = self.settings.payment_request_health_timeout_seconds
                response = await client.get(
                    url,
                    timeout=timeout,
                )
        except httpx.RequestError:
            return False

        return response.status_code < 400
