from datetime import date

from pydantic import BaseModel


class TesCurvePoint(BaseModel):
    security_id: str
    maturity_date: date

    close_price: float | None
    close_yield: float | None

    change_1d_bp: float | None
    change_5d_bp: float | None

    nominal_volume_cop_mn: float
    trade_count: int


class TesCurveResponse(BaseModel):
    trade_date: date
    latest_date: date
    previous_date: date | None
    next_date: date | None
    available_dates: list[date]
    points: list[TesCurvePoint]
