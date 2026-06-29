from fastapi import FastAPI

from app.adapters.http.health import router as health_router
from app.adapters.http.routes import router

app = FastAPI(title="OnyxPay API gateway")

app.include_router(health_router)
app.include_router(router)
