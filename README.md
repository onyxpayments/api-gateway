# OnyxPay API Gateway

Public HTTP entry point for the OnyxPay payment platform.

The gateway validates client requests, forwards them to the Payment Request
Service, and translates upstream failures into stable HTTP responses. It does
not persist transactions, publish RabbitMQ events, or call providers directly.

It also provides structured JSON access logs, correlation ID propagation,
optional HTTP Basic authentication, and single-instance rate limiting.

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
AUTHORIZATION="$(printf 'merchant:secret-key' | base64)"

curl --request POST http://localhost:8003/payments \
  --header "Content-Type: application/json" \
  --header "Authorization: Basic ${AUTHORIZATION}" \
  --header "X-Correlation-ID: merchant-request-123" \
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

Every response includes `X-Correlation-ID`. A valid incoming value is
preserved and forwarded to the Payment Request Service; otherwise the Gateway
generates a UUID.

## Authentication decision

The merchant API supports HTTP Basic authentication:

```text
Authorization: Basic base64(username:secret)
```

Enable it with `API_BASIC_AUTH_ENABLED=true`. Credentials are compared using
constant-time comparisons. Missing or invalid credentials return `401` with a
`WWW-Authenticate: Basic` response header.

Basic authentication uses Base64 encoding, not encryption. It must only be
enabled behind HTTPS. The local browser demo enables it with development-only
credentials supplied through `infra/.env`; never reuse those credentials in a
shared or production environment. Production merchants should call the Gateway
from their backend.

Health endpoints and OpenAPI documentation remain public.

## Rate limiting decision

`POST /payments` uses a fixed-window limiter. Authenticated traffic is grouped
by username; when Basic authentication is disabled, traffic is grouped by
client IP.

The default is 60 requests per 60 seconds. Exceeded limits return `429` and a
`Retry-After` header.

The current limiter is intentionally in memory because the MVP runs one API
Gateway replica. Before horizontal scaling, replace it with Redis or an
infrastructure-level rate limiter so all replicas share counters.

## Structured logging

Application and HTTP access logs are emitted as one-line JSON records:

```json
{
  "timestamp": "2026-06-29T12:00:00+00:00",
  "level": "INFO",
  "service": "api-gateway",
  "logger": "app.adapters.http.middleware",
  "message": "http_request_completed",
  "correlation_id": "merchant-request-123",
  "http_method": "POST",
  "http_path": "/payments",
  "http_status": 202,
  "duration_ms": 12.4
}
```

Upstream logs add `payment_id` and `upstream_status` without logging customer
identity, authorization headers, or secrets. Alloy collects these records and
forwards them to Loki in the Compose stack.

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
| `API_BASIC_AUTH_ENABLED` | `false` |
| `API_BASIC_AUTH_USERNAME` | empty |
| `API_BASIC_AUTH_SECRET` | empty |
| `RATE_LIMIT_ENABLED` | `true` |
| `RATE_LIMIT_REQUESTS` | `60` |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` |

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
│   │   ├── observability     # Correlation context and JSON logging
│   │   ├── security          # Basic authentication and rate limiting
│   │   └── settings.py
│   ├── bootstrap.py
│   └── main.py
├── tests
├── Dockerfile
├── makefile
└── requirements.txt
```

## Current limitations

- Basic authentication supports one environment-configured merchant account.
- The in-memory rate limiter is not suitable for multiple Gateway replicas.
- Request idempotency is not implemented.
- CORS is not configured for arbitrary browser origins.
