from fastapi import APIRouter

from colombia_markets.api.routes.fx import router as fx_router
from colombia_markets.api.routes.health import router as health_router
from colombia_markets.api.routes.macro import router as macro_router
from colombia_markets.api.routes.rates import router as rates_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(rates_router, tags=["rates"])
api_router.include_router(fx_router, tags=["fx"])
api_router.include_router(macro_router, tags=["macro"])
