"""Official Colombian macroeconomic-data endpoints."""

from datetime import date

from fastapi import APIRouter, HTTPException, Query

from colombia_markets.schemas.macro import (
    MacroSeriesCatalogResponse,
    MacroSeriesHistoryResponse,
    MacroSnapshotResponse,
)
from colombia_markets.services.macro import (
    get_macro_catalog,
    get_macro_series_history,
    get_macro_snapshot,
)


router = APIRouter(prefix="/macro")


@router.get("/snapshot", response_model=MacroSnapshotResponse)
def macro_snapshot() -> MacroSnapshotResponse:
    try:
        return get_macro_snapshot()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/series", response_model=MacroSeriesCatalogResponse)
def macro_series_catalog() -> MacroSeriesCatalogResponse:
    try:
        return get_macro_catalog()
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/series/{series_key}", response_model=MacroSeriesHistoryResponse)
def macro_series_history(
    series_key: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Query(default=5000, ge=1, le=10000),
) -> MacroSeriesHistoryResponse:
    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be <= end_date")

    try:
        return get_macro_series_history(
            series_key=series_key,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 422 if message.startswith("Unknown macro series key") else 404
        raise HTTPException(status_code=status_code, detail=message) from exc
