from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


VALID_PAYLOAD = {
    "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
    "amount": 10000,
    "currency": "COP",
    "customer": {
        "first_name": "Juan",
        "last_name": "Bello",
        "personal_id": "123456789",
    },
}


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("app.api.routes.httpx.AsyncClient.post", new_callable=AsyncMock)
def test_create_payment_returns_pending_from_orchestrator(mock_post):
    mock_post.return_value = httpx.Response(
        status_code=200,
        json={
            "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
            "provider_transaction_id": "mock_123e4567-e89b-12d3-a456-426614174000",
            "status": "PENDING",
            "message": "Payment authorization is being processed",
        },
    )

    response = client.post("/payments", json=VALID_PAYLOAD)

    assert response.status_code == 200

    data = response.json()

    assert data["transaction_id"] == VALID_PAYLOAD["transaction_id"]
    assert data["provider_transaction_id"] == f"mock_{VALID_PAYLOAD['transaction_id']}"
    assert data["status"] == "PENDING"
    assert data["message"] == "Payment authorization is being processed"

    mock_post.assert_called_once()

    url = mock_post.call_args.args[0]
    body = mock_post.call_args.kwargs["json"]

    assert url.endswith("/transactions")
    assert body["transaction_id"] == VALID_PAYLOAD["transaction_id"]
    assert body["amount"] == VALID_PAYLOAD["amount"]
    assert body["currency"] == VALID_PAYLOAD["currency"]
    assert body["customer"]["first_name"] == "Juan"
    assert body["customer"]["personal_id"] == "123456789"


def test_create_payment_rejects_missing_customer():
    payload = {
        "transaction_id": "trx_123",
        "amount": 10000,
        "currency": "COP",
    }

    response = client.post("/payments", json=payload)

    assert response.status_code == 422


def test_create_payment_rejects_missing_customer_personal_id():
    payload = {
        "transaction_id": "trx_123",
        "amount": 10000,
        "currency": "COP",
        "customer": {
            "first_name": "Juan",
            "last_name": "Bello",
        },
    }

    response = client.post("/payments", json=payload)

    assert response.status_code == 422


def test_create_payment_rejects_missing_currency():
    payload = {
        "transaction_id": "trx_123",
        "amount": 10000,
        "customer": {
            "first_name": "Juan",
            "last_name": "Bello",
            "personal_id": "123456789",
        },
    }

    response = client.post("/payments", json=payload)

    assert response.status_code == 422


@patch("app.api.routes.httpx.AsyncClient.post", new_callable=AsyncMock)
def test_create_payment_returns_orchestrator_error(mock_post):
    mock_post.return_value = httpx.Response(
        status_code=400,
        json={"detail": "Invalid transaction"},
    )

    response = client.post("/payments", json=VALID_PAYLOAD)

    assert response.status_code == 400
    assert response.json() == {"detail": {"detail": "Invalid transaction"}}


@patch("app.api.routes.httpx.AsyncClient.post", new_callable=AsyncMock)
def test_create_payment_returns_502_when_orchestrator_unavailable(mock_post):
    mock_post.side_effect = httpx.RequestError("Connection failed")

    response = client.post("/payments", json=VALID_PAYLOAD)

    assert response.status_code == 502
    assert "Could not reach payment orchestrator" in response.json()["detail"]


@patch("app.api.routes.httpx.AsyncClient.post", new_callable=AsyncMock)
def test_create_payment_returns_502_when_orchestrator_response_is_invalid(mock_post):
    mock_post.return_value = httpx.Response(
        status_code=200,
        json={
            "transaction_id": VALID_PAYLOAD["transaction_id"],
            "status": "PENDING",
            "message": "Payment authorization is being processed",
        },
    )

    response = client.post("/payments", json=VALID_PAYLOAD)

    assert response.status_code == 502
    assert "Missing field" in response.json()["detail"]
