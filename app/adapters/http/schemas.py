from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


class ApiSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CustomerRequest(ApiSchema):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    personal_id: str = Field(min_length=1, max_length=50)


class PaymentRequest(ApiSchema):
    transaction_id: UUID
    amount: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    notification_url: HttpUrl
    customer: CustomerRequest

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class PaymentAcceptedResponse(ApiSchema):
    transaction_id: UUID
    status: str
    message: str | None = None
