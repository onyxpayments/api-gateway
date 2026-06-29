from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient

from app.application.exceptions import (
    InvalidPaymentRequestResponse,
    PaymentRequestRejected,
    PaymentRequestUnavailable,
)
from app.application.results import PaymentSubmissionResult
from app.application.use_cases.submit_payment import SubmitPaymentUseCase
from app.bootstrap import (
    get_payment_request_gateway,
    get_submit_payment_use_case,
)
from app.main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
    "amount": "10000.50",
    "currency": "cop",
    "notification_url": "https://merchant.example/webhooks/payments",
    "customer": {
        "first_name": "Juan",
        "last_name": "Bello",
        "personal_id": "123456789",
    },
}


class FakePaymentRequestGateway:
    def __init__(self, result=None, error=None, ready=True):
        self.result = result
        self.error = error
        self.ready = ready
        self.commands = []

    async def submit(self, command):
        self.commands.append(command)
        if self.error is not None:
            raise self.error
        return self.result

    async def is_ready(self):
        return self.ready


def setup_function():
    app.dependency_overrides.clear()


def teardown_function():
    app.dependency_overrides.clear()


def override_submit_use_case(gateway):
    use_case = SubmitPaymentUseCase(gateway)
    app.dependency_overrides[get_submit_payment_use_case] = lambda: use_case


def test_health_returns_ok():
    assert client.get("/health").json() == {"status": "ok"}


def test_liveness_returns_alive():
    assert client.get("/health/live").json() == {"status": "alive"}


def test_startup_returns_started():
    assert client.get("/health/startup").json() == {"status": "started"}


def test_readiness_returns_ready_when_payment_request_is_ready():
    gateway = FakePaymentRequestGateway(ready=True)
    app.dependency_overrides[get_payment_request_gateway] = lambda: gateway

    response = client.get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"payment_request_service": "up"},
    }


def test_readiness_returns_503_when_payment_request_is_unavailable():
    gateway = FakePaymentRequestGateway(ready=False)
    app.dependency_overrides[get_payment_request_gateway] = lambda: gateway

    response = client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "checks": {"payment_request_service": "down"},
    }


def test_submit_payment_routes_to_payment_request_service():
    payment_id = UUID(VALID_PAYLOAD["transaction_id"])
    gateway = FakePaymentRequestGateway(
        result=PaymentSubmissionResult(
            payment_id=payment_id,
            status="RECEIVED",
            message="Payment request accepted for processing",
        )
    )
    override_submit_use_case(gateway)

    response = client.post("/payments", json=VALID_PAYLOAD)

    assert response.status_code == 202
    assert response.json() == {
        "transaction_id": str(payment_id),
        "status": "RECEIVED",
        "message": "Payment request accepted for processing",
    }
    command = gateway.commands[0]
    assert command.payment_id == payment_id
    assert command.amount == Decimal("10000.50")
    assert command.currency == "COP"
    assert command.notification_url == VALID_PAYLOAD["notification_url"]


def test_submit_payment_rejects_invalid_payload():
    payload = {**VALID_PAYLOAD, "amount": 0}

    response = client.post("/payments", json=payload)

    assert response.status_code == 422


def test_submit_payment_requires_notification_url():
    payload = dict(VALID_PAYLOAD)
    payload.pop("notification_url")

    response = client.post("/payments", json=payload)

    assert response.status_code == 422


def test_submit_payment_returns_502_when_service_is_unavailable():
    message = "Could not reach payment request service"
    error = PaymentRequestUnavailable(message)
    gateway = FakePaymentRequestGateway(error=error)
    override_submit_use_case(gateway)

    response = client.post("/payments", json=VALID_PAYLOAD)

    assert response.status_code == 502
    assert response.json() == {"detail": message}


def test_submit_payment_propagates_service_rejection():
    gateway = FakePaymentRequestGateway(
        error=PaymentRequestRejected(
            status_code=503,
            detail={"detail": "RabbitMQ unavailable"},
        )
    )
    override_submit_use_case(gateway)

    response = client.post("/payments", json=VALID_PAYLOAD)

    assert response.status_code == 503
    assert response.json() == {"detail": {"detail": "RabbitMQ unavailable"}}


def test_submit_payment_returns_502_for_invalid_upstream_response():
    gateway = FakePaymentRequestGateway(
        error=InvalidPaymentRequestResponse(
            "Payment request service returned an invalid response"
        )
    )
    override_submit_use_case(gateway)

    response = client.post("/payments", json=VALID_PAYLOAD)

    assert response.status_code == 502
