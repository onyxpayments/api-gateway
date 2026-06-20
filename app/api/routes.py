from fastapi import APIRouter, HTTPException
import httpx

from app.api.schemas import AuthorizationRequest, AuthorizationResponse
from app.infraestructure.settings import settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/payments", response_model=AuthorizationResponse)
async def create_payment(request: AuthorizationRequest):
    orchestrator_url = f"{settings.orchestrator_url}/transactions"

    try:
        async with httpx.AsyncClient() as client:
            orchestrator_response = await client.post(
                orchestrator_url,
                json=request.model_dump(mode="json"),
                timeout=10,
            )

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Could not reach payment orchestrator: {str(error)}",
        )

    if orchestrator_response.status_code >= 400:
        raise HTTPException(
            status_code=orchestrator_response.status_code,
            detail=orchestrator_response.json(),
        )

    response_data = orchestrator_response.json()

    try:
        return AuthorizationResponse(
            transaction_id=response_data["transaction_id"],
            provider_transaction_id=response_data["provider_transaction_id"],
            status=response_data["status"],
            message=response_data["message"],
        )

    except KeyError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Invalid response from payment orchestrator. Missing field: {str(error)}",
        )
