from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class PaymentSubmissionResult:
    payment_id: UUID
    status: str
    message: str | None = None
