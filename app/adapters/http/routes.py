from fastapi import APIRouter, Depends, HTTPException, status

from app.adapters.http import schemas
from app.application.commands import SubmitPaymentCommand
from app.application.exceptions import (
    InvalidPaymentRequestResponse,
    PaymentRequestRejected,
    PaymentRequestUnavailable,
)
from app.application.use_cases.submit_payment import SubmitPaymentUseCase
from app.bootstrap import get_submit_payment_use_case
from app.domain.models import Customer

router = APIRouter()


@router.post(
    "/payments",
    response_model=schemas.PaymentAcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_payment(
    request: schemas.PaymentRequest,
    use_case: SubmitPaymentUseCase = Depends(get_submit_payment_use_case),
):
    command = SubmitPaymentCommand(
        payment_id=request.transaction_id,
        amount=request.amount,
        currency=request.currency,
        customer=Customer(
            first_name=request.customer.first_name,
            last_name=request.customer.last_name,
            personal_id=request.customer.personal_id,
        ),
    )

    try:
        result = await use_case.execute(command)
    except PaymentRequestUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error
    except PaymentRequestRejected as error:
        raise HTTPException(
            status_code=error.status_code,
            detail=error.detail,
        ) from error
    except InvalidPaymentRequestResponse as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(error),
        ) from error

    return schemas.PaymentAcceptedResponse(
        transaction_id=result.payment_id,
        status=result.status,
        message=result.message,
    )
