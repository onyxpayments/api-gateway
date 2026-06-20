from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="OnyxPay API gateway")

app.include_router(router)
