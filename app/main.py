from fastapi import FastAPI

from app.adapters.http.health import router as health_router
from app.adapters.http.middleware import request_observability_middleware
from app.adapters.http.routes import router
from app.infrastructure.observability.logging import configure_logging
from app.infrastructure.settings import settings

configure_logging(settings.service_name)

app = FastAPI(title="OnyxPay API Gateway")
app.middleware("http")(request_observability_middleware)

app.include_router(health_router)
app.include_router(router)
