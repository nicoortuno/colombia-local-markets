from datetime import date

from fastapi import APIRouter, HTTPException, Query

from colombia_markets.schemas.tes import TesCurveResponse
from colombia_markets.services.rates import get_tes_curve


router = APIRouter(
    prefix="/rates",
)


@router.get(
    "/curve",
    response_model=TesCurveResponse,
)
def tes_curve(
    trade_date: date | None = Query(
        default=None,
        description=(
            "Trading date. Defaults to latest available. "
            "If the requested date is not a trading day, "
            "the latest available date on or before it is returned."
        ),
    ),
) -> TesCurveResponse:
    try:
        return get_tes_curve(
            trade_date=trade_date
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
