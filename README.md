# OnyxPay API Gateway

Public HTTP entry point for the OnyxPay payment platform.

The API Gateway exposes a small client-facing API, validates incoming payloads,
forwards payment requests to the Payment Request Service, and translates
upstream failures into HTTP responses. It does not store transactions or
communicate with payment providers directly.

## Responsibilities

- Expose the public payment API.
- Validate requests with Pydantic.
- Forward valid requests to the Payment Request Service.
- Return a stable response shape to clients.
- Report upstream connectivity and contract errors.
- Provide interactive OpenAPI documentation through FastAPI.

## Request Flow

```text
Client
  │
  │ POST /payments
  ▼
API Gateway
  │
  │ POST /payments
  ▼
Payment Request Service → RabbitMQ
```

## API

When the full platform is running through the infrastructure repository, the
gateway is available at `http://localhost:8003`.

### Health Check

```http
GET /health
```

Response:

```json
{
  "status": "ok"
}
```

### Create Payment

```http
POST /payments
Content-Type: application/json
```

Request:

```json
{
  "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
  "amount": 10000,
  "currency": "COP",
  "customer": {
    "first_name": "Juan",
    "last_name": "Bello",
    "personal_id": "123456789"
  }
}
```

Example:

```bash
curl -X POST http://localhost:8003/payments \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
    "amount": 10000,
    "currency": "COP",
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

The identifier supplied by the client becomes the payment identifier used in
the asynchronous event flow.

### Error Behavior

- `422 Unprocessable Entity`: the request does not match the expected schema.
- `502 Bad Gateway`: the Payment Request Service cannot be reached or returns
  an invalid response.
- Other upstream HTTP errors are returned with the service's status code.

Interactive API documentation:

```text
http://localhost:8003/docs
```

## Running the Full Platform

The recommended development path is the infrastructure repository:

```bash
cd ../infra
docker compose pull
docker compose up -d
```

The gateway uses the internal Compose address
`http://payment-request-service:8003`.

## Local Development

Requirements:

- Python 3.13
- Make

Install dependencies in a virtual environment:

```bash
make install
```

Run the service:

```bash
.venv/bin/uvicorn app.main:app --reload --port 8002
```

Run quality checks:

```bash
make format
make lint
make test
```

Set `PAYMENT_REQUEST_SERVICE_URL` when running outside the Compose network.

## Docker

Build and run the image:

```bash
docker build -t api-gateway .
docker run --rm -p 8003:8002 api-gateway
```

The published platform image is:

```text
ghcr.io/onyxpayments/api-gateway:latest
```

## Project Structure

```text
.
├── app
│   ├── adapters
│   │   └── http            # FastAPI routes, schemas and health probes
│   ├── application
│   │   ├── use_cases       # Submit payment orchestration
│   │   ├── commands.py
│   │   ├── exceptions.py
│   │   ├── ports.py
│   │   └── results.py
│   ├── domain              # Transport-independent payment models
│   ├── infrastructure
│   │   ├── clients         # Payment Request Service HTTP adapter
│   │   └── settings.py
│   ├── bootstrap.py        # Dependency composition
│   └── main.py
├── tests                   # API, use-case and client adapter tests
├── Dockerfile
├── makefile
└── requirements.txt
```

## CI/CD

GitHub Actions runs formatting checks, tests, and a Docker build on pull
requests and pushes to `main`. Pushes to `main` publish two images to GitHub
Container Registry:

```text
ghcr.io/onyxpayments/api-gateway:latest
ghcr.io/onyxpayments/api-gateway:<commit-sha>
```

## Current Limitations

- Authentication, authorization, rate limiting, and idempotency are not
  implemented.
- The gateway does not currently emit structured application logs.

## Health probes

- `GET /health/live` checks that the API process can respond.
- `GET /health/startup` confirms application startup completed.
- `GET /health/ready` checks that the Payment Request Service is ready.
- `GET /health` remains available for backward compatibility.
