from fastapi import Depends, FastAPI
from app.routers import health, events, risk
from app.logging_middleware import RequestLoggingMiddleware
from app.rate_limit import rate_limit
from app.security import require_api_key

app = FastAPI(
    title="SoroWatch API",
    description="Coordinates the AI scoring agent and the on-chain risk registry.",
    version="0.1.0",
)

app.add_middleware(RequestLoggingMiddleware)

app.include_router(health.router)
app.include_router(
    events.router,
    prefix="/events",
    tags=["events"],
    dependencies=[Depends(require_api_key)],
)
app.include_router(
    risk.router,
    prefix="/risk",
    tags=["risk"],
    # Auth runs first, so requests with a bad key never use up the limit.
    dependencies=[Depends(require_api_key), Depends(rate_limit)],
)
