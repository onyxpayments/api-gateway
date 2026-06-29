import re
from contextvars import ContextVar, Token
from uuid import uuid4

CORRELATION_ID_HEADER = "X-Correlation-ID"
CORRELATION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

correlation_id_context: ContextVar[str | None] = ContextVar(
    "correlation_id",
    default=None,
)


def valid_or_new_correlation_id(value: str | None) -> str:
    if value and CORRELATION_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid4())


def set_correlation_id(correlation_id: str) -> Token:
    return correlation_id_context.set(correlation_id)


def reset_correlation_id(token: Token) -> None:
    correlation_id_context.reset(token)


def get_correlation_id() -> str | None:
    return correlation_id_context.get()
