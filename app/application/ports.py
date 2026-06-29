from typing import Protocol

from app.application.commands import SubmitPaymentCommand
from app.application.results import PaymentSubmissionResult


class PaymentRequestGateway(Protocol):
    async def submit(
        self,
        command: SubmitPaymentCommand,
    ) -> PaymentSubmissionResult: ...

    async def is_ready(self) -> bool: ...
