import logging
from time import perf_counter

from fastapi import Request

from app.infrastructure.observability.context import (
    CORRELATION_ID_HEADER,
    reset_correlation_id,
    set_correlation_id,
    valid_or_new_correlation_id,
)

logger = logging.getLogger(__name__)


async def request_observability_middleware(request: Request, call_next):
    correlation_id = valid_or_new_correlation_id(
        request.headers.get(CORRELATION_ID_HEADER)
    )
    token = set_correlation_id(correlation_id)
    started_at = perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "http_request_failed",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "duration_ms": round(
                    (perf_counter() - started_at) * 1000,
                    2,
                ),
            },
        )
        raise
    else:
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        logger.info(
            "http_request_completed",
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": round(
                    (perf_counter() - started_at) * 1000,
                    2,
                ),
            },
        )
        return response
    finally:
        reset_correlation_id(token)
