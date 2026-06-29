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
            "customer": {
                "first_name": command.customer.first_name,
                "last_name": command.customer.last_name,
                "personal_id": command.customer.personal_id,
            },
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    json=payload,
                    timeout=self.settings.payment_request_timeout_seconds,
                )
        except httpx.RequestError as error:
            raise PaymentRequestUnavailable(
                "Could not reach payment request service"
            ) from error

        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise PaymentRequestRejected(response.status_code, detail)

        try:
            response_body = response.json()
            validate = PaymentRequestServiceResponse.model_validate
            upstream = validate(response_body)
        except (ValueError, ValidationError) as error:
            raise InvalidPaymentRequestResponse(
                "Payment request service returned an invalid response"
            ) from error

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
