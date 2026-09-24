"""Vendor-labelled daily USD/COP quotes (not the official Colombian TRM)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from colombia_markets.db.base import Base


class FxDailyMarket(Base):
    __tablename__ = "fx_daily_market"

    __table_args__ = (
        UniqueConstraint(
            "trade_date", "pair", "source", name="uq_fx_daily_market_date_pair_source"
        ),
        Index("ix_fx_daily_market_pair_source_date", "pair", "source", "trade_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    pair: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    open_price: Mapped[Decimal] = mapped_column(Numeric(16, 6), nullable=False)
    high_price: Mapped[Decimal] = mapped_column(Numeric(16, 6), nullable=False)
    low_price: Mapped[Decimal] = mapped_column(Numeric(16, 6), nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(16, 6), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
