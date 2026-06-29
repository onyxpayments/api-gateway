import json
import logging
from datetime import datetime, timezone

from app.infrastructure.observability.context import get_correlation_id

STANDARD_LOG_RECORD_FIELDS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
)


class JsonFormatter(logging.Formatter):
    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
        }
        correlation_id = getattr(
            record,
            "correlation_id",
            get_correlation_id(),
        )
        if correlation_id:
            payload["correlation_id"] = correlation_id

        for key, value in record.__dict__.items():
            if key not in STANDARD_LOG_RECORD_FIELDS and key not in {
                "color_message",
                "correlation_id",
            }:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str)


def configure_logging(service_name: str, level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter(service_name))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)

    for logger_name in ("uvicorn", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True

    logging.getLogger("uvicorn.access").disabled = True
