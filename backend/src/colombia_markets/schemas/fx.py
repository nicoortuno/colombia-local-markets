"""Public USD/COP response schemas. All prices are COP per one USD."""

from datetime import date

from pydantic import BaseModel, Field


class FxDailyPoint(BaseModel):
    trade_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    change_1d_cop: float | None = None
    change_1d_pct: float | None = None


class FxHistoryResponse(BaseModel):
    pair: str = "USD/COP"
    source: str = "yahoo_finance"
    latest_date: date
    points: list[FxDailyPoint] = Field(default_factory=list)


class FxLatestResponse(BaseModel):
    pair: str = "USD/COP"
    source: str = "yahoo_finance"
    latest_date: date
    point: FxDailyPoint
