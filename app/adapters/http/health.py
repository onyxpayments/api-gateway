from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.application.ports import PaymentRequestGateway
from app.bootstrap import get_payment_request_gateway

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/live")
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/startup")
def startup() -> dict[str, str]:
    return {"status": "started"}


@router.get("/ready")
async def readiness(
    gateway: PaymentRequestGateway = Depends(get_payment_request_gateway),
):
    if not await gateway.is_ready():
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "checks": {"payment_request_service": "down"},
            },
        )

    return {
        "status": "ready",
        "checks": {"payment_request_service": "up"},
    }
