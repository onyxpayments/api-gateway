from decimal import Decimal
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from app.application.commands import SubmitPaymentCommand
from app.application.exceptions import (
    InvalidPaymentRequestResponse,
    PaymentRequestRejected,
    PaymentRequestUnavailable,
)
from app.domain.models import Customer
from app.infrastructure.clients.payment_request_service import (
    HttpPaymentRequestGateway,
)
from app.infrastructure.observability.context import (
    reset_correlation_id,
    set_correlation_id,
)
from app.infrastructure.settings import Settings

CLIENT_MODULE = "app.infrastructure.clients.payment_request_service"
POST_PATCH_TARGET = f"{CLIENT_MODULE}.httpx.AsyncClient.post"


def create_command():
    return SubmitPaymentCommand(
        payment_id=uuid4(),
        amount=Decimal("10000.50"),
        currency="COP",
        notification_url="https://merchant.example/webhooks/payments",
        customer=Customer(
            first_name="Juan",
            last_name="Bello",
            personal_id="123456789",
        ),
    )


@pytest.mark.asyncio
@patch(
    POST_PATCH_TARGET,
    new_callable=AsyncMock,
)
async def test_client_submits_payment_request(mock_post):
    command = create_command()
    mock_post.return_value = httpx.Response(
        status_code=202,
        json={
            "transaction_id": str(command.payment_id),
            "status": "RECEIVED",
            "message": "Accepted",
        },
    )
    gateway = HttpPaymentRequestGateway(Settings(_env_file=None))

    token = set_correlation_id("correlation-123")
    try:
        result = await gateway.submit(command)
    finally:
        reset_correlation_id(token)

    assert result.payment_id == command.payment_id
    assert result.status == "RECEIVED"
    assert mock_post.call_args.args[0].endswith("/payments")
    assert mock_post.call_args.kwargs["json"]["amount"] == "10000.50"
    assert mock_post.call_args.kwargs["json"]["notification_url"] == (
        command.notification_url
    )
    assert mock_post.call_args.kwargs["headers"] == {
        "X-Correlation-ID": "correlation-123"
    }


@pytest.mark.asyncio
@patch(
    POST_PATCH_TARGET,
    new_callable=AsyncMock,
)
async def test_client_translates_connectivity_errors(mock_post):
    mock_post.side_effect = httpx.RequestError("Connection failed")
    gateway = HttpPaymentRequestGateway(Settings(_env_file=None))

    with pytest.raises(PaymentRequestUnavailable):
        await gateway.submit(create_command())


@pytest.mark.asyncio
@patch(
    POST_PATCH_TARGET,
    new_callable=AsyncMock,
)
async def test_client_translates_upstream_rejection(mock_post):
    mock_post.return_value = httpx.Response(
        status_code=503,
        json={"detail": "RabbitMQ unavailable"},
    )
    gateway = HttpPaymentRequestGateway(Settings(_env_file=None))

    with pytest.raises(PaymentRequestRejected) as captured:
        await gateway.submit(create_command())

    assert captured.value.status_code == 503


@pytest.mark.asyncio
@patch(
    POST_PATCH_TARGET,
    new_callable=AsyncMock,
)
async def test_client_rejects_invalid_success_response(mock_post):
    mock_post.return_value = httpx.Response(
        status_code=202,
        json={"status": "RECEIVED"},
    )
    gateway = HttpPaymentRequestGateway(Settings(_env_file=None))

    with pytest.raises(InvalidPaymentRequestResponse):
        await gateway.submit(create_command())
