# OnyxPay API Gateway

Public HTTP entry point for the OnyxPay payment platform.

The gateway validates client requests, forwards them to the Payment Request
Service, and translates upstream failures into stable HTTP responses. It does
not persist transactions, publish RabbitMQ events, or call providers directly.

## Flow

```text
Client
  │ POST /payments
  ▼
API Gateway
  │ POST /payments
  ▼
Payment Request Service
  │ payment.requested.v1
  ▼
RabbitMQ
```

## API

With the full Compose stack running, the gateway is available at
`http://localhost:8003`; the container listens on port `8002`.

### Create a payment

```http
POST /payments
Content-Type: application/json
```

```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "amount": "10000.50",
  "currency": "COP",
  "notification_url": "https://merchant.example/webhooks/payments",
  "customer": {
    "first_name": "Juan",
    "last_name": "Bello",
    "personal_id": "123456789"
  }
}
```

Field rules:

- `transaction_id` must be a UUID.
- `amount` must be greater than zero.
- `currency` must contain exactly three characters and is normalized to
  uppercase.
- `notification_url` is required and must be a valid HTTP or HTTPS URL.
- Customer names and personal ID must be non-empty and respect their schema
  length limits.
- Unknown fields are rejected.

Example:

```bash
curl --request POST http://localhost:8003/payments \
  --header "Content-Type: application/json" \
  --data '{
    "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
    "amount": "10000.50",
    "currency": "COP",
    "notification_url": "https://merchant.example/webhooks/payments",
    "customer": {
      "first_name": "Juan",
      "last_name": "Bello",
      "personal_id": "123456789"
    }
  }'
```

Successful response:

```http
HTTP/1.1 202 Accepted
```

```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "RECEIVED",
  "message": "Payment request accepted for processing"
}
```

This response confirms that the downstream service accepted the request for
asynchronous processing. It is not a final payment status.

### Error behavior

- `422 Unprocessable Entity`: invalid client contract.
- `502 Bad Gateway`: the Payment Request Service cannot be reached or returns
  an invalid success response.
- Other upstream HTTP failures retain the upstream status and detail.

Interactive OpenAPI documentation is available at
`http://localhost:8003/docs`.

## Configuration

| Variable | Default |
| --- | --- |
| `PAYMENT_REQUEST_SERVICE_URL` | `http://payment-request-service:8003` |
| `PAYMENT_REQUEST_TIMEOUT_SECONDS` | `10` |
| `PAYMENT_REQUEST_HEALTH_TIMEOUT_SECONDS` | `2` |

For a locally running Payment Request Service:

```dotenv
PAYMENT_REQUEST_SERVICE_URL=http://localhost:8004
```

## Health checks

- `GET /health/live`: gateway process liveness.
- `GET /health/startup`: application startup.
- `GET /health/ready`: Payment Request Service readiness.
- `GET /health`: backward-compatible basic check.

## Local development

Requirements: Python 3.13 and a reachable Payment Request Service.

```bash
make install
make format
make lint
make test
.venv/bin/uvicorn app.main:app --reload --port 8002
```

## Docker and Compose

```bash
docker build -t api-gateway .
docker run --rm -p 8003:8002 \
  -e PAYMENT_REQUEST_SERVICE_URL=http://host.docker.internal:8004 \
  api-gateway
```

Published image:

```text
ghcr.io/onyxpayments/api-gateway:latest
```

Run the full platform from the infrastructure repository:

```bash
cd ../infra
docker compose pull
docker compose up -d
```

## Project structure

```text
.
├── app
│   ├── adapters/http          # Public routes, schemas, and health checks
│   ├── application           # Submit command, use case, ports, and results
│   ├── domain                # Transport-independent request models
│   ├── infrastructure
│   │   ├── clients           # Payment Request Service HTTP adapter
│   │   └── settings.py
│   ├── bootstrap.py
│   └── main.py
├── tests
├── Dockerfile
├── makefile
└── requirements.txt
```

## Current limitations

- Authentication, authorization, rate limiting, and request idempotency are
  not implemented.
- CORS is not configured for arbitrary browser origins.
