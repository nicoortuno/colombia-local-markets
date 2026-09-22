from fastapi import APIRouter

from colombia_markets.api.routes.health import (
    router as health_router,
)
from colombia_markets.api.routes.rates import (
    router as rates_router,
)


api_router = APIRouter()

api_router.include_router(
    health_router,
    tags=["health"],
)

api_router.include_router(
    rates_router,
    tags=["rates"],
)
