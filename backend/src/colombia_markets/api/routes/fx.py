"""Daily Yahoo USD/COP market-data endpoints."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from colombia_markets.schemas.fx import FxHistoryResponse, FxLatestResponse
from colombia_markets.services.fx import get_latest_usdcop, get_usdcop_history

router = APIRouter(prefix="/fx")


@router.get("/usdcop/latest", response_model=FxLatestResponse)
def usdcop_latest() -> FxLatestResponse:
    try:
        return get_latest_usdcop()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/usdcop/history", response_model=FxHistoryResponse)
def usdcop_history(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=2000, ge=1, le=5000),
) -> FxHistoryResponse:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be <= end_date")
    try:
        return get_usdcop_history(start_date, end_date, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
