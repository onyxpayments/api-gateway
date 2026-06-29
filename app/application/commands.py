from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from app.domain.models import Customer


@dataclass(frozen=True)
class SubmitPaymentCommand:
    payment_id: UUID
    amount: Decimal
    currency: str
    notification_url: str
    customer: Customer
