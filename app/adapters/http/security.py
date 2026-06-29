from fastapi import Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.bootstrap import get_gateway_access_policy
from app.infrastructure.security.access_policy import GatewayAccessPolicy

basic_auth = HTTPBasic(auto_error=False)


def enforce_gateway_access(
    request: Request,
    credentials: HTTPBasicCredentials | None = Depends(basic_auth),
    policy: GatewayAccessPolicy = Depends(get_gateway_access_policy),
) -> None:
    client_id = request.client.host if request.client else "unknown"
    policy.enforce(
        username=credentials.username if credentials else None,
        secret=credentials.password if credentials else None,
        client_id=client_id,
    )
