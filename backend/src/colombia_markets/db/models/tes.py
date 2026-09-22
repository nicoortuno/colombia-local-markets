from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from colombia_markets.db.base import Base


class TesDailyMarket(Base):
    __tablename__ = "tes_daily_market"

    __table_args__ = (
        UniqueConstraint(
            "trade_date",
            "security_id",
            name="uq_tes_daily_market_date_security",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    trade_date: Mapped[date] = mapped_column(
        Date,
        index=True,
    )

    security_id: Mapped[str] = mapped_column(
        String(32),
        index=True,
    )

    maturity_date: Mapped[date] = mapped_column(
        Date,
        index=True,
    )

    nominal_volume_cop_mn: Mapped[Decimal] = mapped_column(
        Numeric(20, 2),
    )

    trade_count: Mapped[int] = mapped_column(
        Integer,
    )

    open_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
    )

    open_yield: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
    )

    min_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
    )

    yield_at_min_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
    )

    avg_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
    )

    avg_yield: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
    )

    max_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
    )

    yield_at_max_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
    )

    close_price: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
    )

    close_yield: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 6),
    )

    source_url: Mapped[str | None] = mapped_column(
        String(512),
    )

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
