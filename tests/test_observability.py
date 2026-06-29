import json
import logging

from app.infrastructure.observability.context import (
    reset_correlation_id,
    set_correlation_id,
)
from app.infrastructure.observability.logging import JsonFormatter


def test_json_formatter_includes_context_and_structured_fields():
    token = set_correlation_id("correlation-123")
    try:
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="payment_forwarded",
            args=(),
            exc_info=None,
        )
        record.payment_id = "payment-123"

        payload = json.loads(JsonFormatter("api-gateway").format(record))
    finally:
        reset_correlation_id(token)

    assert payload["service"] == "api-gateway"
    assert payload["message"] == "payment_forwarded"
    assert payload["correlation_id"] == "correlation-123"
    assert payload["payment_id"] == "payment-123"
