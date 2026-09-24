"""Official Colombian macroeconomic observations fetched through BanRep SUAMECA."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from colombia_markets.db.base import Base


class MacroObservation(Base):
    __tablename__ = "macro_observation"

    __table_args__ = (
        UniqueConstraint(
            "series_key",
            "observation_date",
            name="uq_macro_observation_series_date",
        ),
        Index(
            "ix_macro_observation_series_date",
            "series_key",
            "observation_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    series_key: Mapped[str] = mapped_column(String(40), nullable=False)
    series_name: Mapped[str] = mapped_column(String(180), nullable=False)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    source_series_id: Mapped[int] = mapped_column(Integer, nullable=False)
    periodicity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[str] = mapped_column(String(32), nullable=False)
    unit: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
