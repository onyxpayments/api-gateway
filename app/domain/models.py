from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class Customer:
    first_name: str
    last_name: str
    personal_id: str


@dataclass(frozen=True)
class PaymentRequest:
    payment_id: UUID
    amount: Decimal
    currency: str
    notification_url: str
    customer: Customer
