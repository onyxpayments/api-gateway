from app.application.commands import SubmitPaymentCommand
from app.application.ports import PaymentRequestGateway
from app.application.results import PaymentSubmissionResult


class SubmitPaymentUseCase:
    def __init__(self, payment_request_gateway: PaymentRequestGateway):
        self.payment_request_gateway = payment_request_gateway

    async def execute(
        self,
        command: SubmitPaymentCommand,
    ) -> PaymentSubmissionResult:
        return await self.payment_request_gateway.submit(command)
