"""Persist and query daily Yahoo USD/COP quotes."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from colombia_markets.db.models.fx import FxDailyMarket
from colombia_markets.db.session import SessionLocal
from colombia_markets.ingestion.fx import USD_COP_PAIR, YAHOO_SOURCE
from colombia_markets.schemas.fx import FxDailyPoint, FxHistoryResponse, FxLatestResponse


def upsert_fx_daily_market(records: list[dict]) -> int:
    """Idempotent on (trade_date, pair, source); atomic per download batch."""
    if not records:
        return 0

    with SessionLocal() as session:
        # A large historical backfill can exceed PostgreSQL's bind-parameter
        # ceiling if compiled as one INSERT; execute bounded chunks atomically.
        for offset in range(0, len(records), 500):
            chunk = records[offset : offset + 500]
            statement = insert(FxDailyMarket).values(chunk)
            statement = statement.on_conflict_do_update(
                constraint="uq_fx_daily_market_date_pair_source",
                set_={
                    key: getattr(statement.excluded, key)
                    for key in ("open_price", "high_price", "low_price", "close_price")
                } | {"ingested_at": func.now()},
            )
            session.execute(statement)
        session.commit()
    return len(records)


def get_latest_fx_date() -> date | None:
    with SessionLocal() as session:
        return session.scalar(
            select(func.max(FxDailyMarket.trade_date)).where(
                FxDailyMarket.pair == USD_COP_PAIR,
                FxDailyMarket.source == YAHOO_SOURCE,
            )
        )


def _fx_change(current: Decimal, previous: Decimal | None) -> tuple[float | None, float | None]:
    if previous is None or previous == 0:
        return None, None
    delta = current - previous
    return round(float(delta), 2), round(float(delta / previous * 100), 3)


def get_usdcop_history(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 2000,
) -> FxHistoryResponse:
    if start_date and end_date and start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    if limit < 1 or limit > 5000:
        raise ValueError("limit must be between 1 and 5000")

    with SessionLocal() as session:
        latest = session.scalar(
            select(func.max(FxDailyMarket.trade_date)).where(
                FxDailyMarket.pair == USD_COP_PAIR,
                FxDailyMarket.source == YAHOO_SOURCE,
            )
        )
        if latest is None:
            raise ValueError("No Yahoo USD/COP daily data is available")

        # Default to one year. Explicit date ranges can access all stored history.
        resolved_end = min(end_date or latest, latest)
        resolved_start = start_date or (resolved_end - timedelta(days=365))
        if resolved_start > resolved_end:
            raise ValueError("No USD/COP data in the requested interval")

        where = (
            FxDailyMarket.pair == USD_COP_PAIR,
            FxDailyMarket.source == YAHOO_SOURCE,
            FxDailyMarket.trade_date >= resolved_start,
            FxDailyMarket.trade_date <= resolved_end,
        )
        # Descending limit ensures the most recent days are retained on long ranges.
        descending = session.scalars(
            select(FxDailyMarket)
            .where(*where)
            .order_by(FxDailyMarket.trade_date.desc())
            .limit(limit)
        ).all()
        rows = list(reversed(descending))
        if not rows:
            raise ValueError("No USD/COP data in the requested interval")

        previous_close = session.scalar(
            select(FxDailyMarket.close_price)
            .where(
                FxDailyMarket.pair == USD_COP_PAIR,
                FxDailyMarket.source == YAHOO_SOURCE,
                FxDailyMarket.trade_date < rows[0].trade_date,
            )
            .order_by(FxDailyMarket.trade_date.desc())
            .limit(1)
        )

        points: list[FxDailyPoint] = []
        for row in rows:
            delta_cop, delta_pct = _fx_change(row.close_price, previous_close)
            points.append(
                FxDailyPoint(
                    trade_date=row.trade_date,
                    open_price=float(row.open_price),
                    high_price=float(row.high_price),
                    low_price=float(row.low_price),
                    close_price=float(row.close_price),
                    change_1d_cop=delta_cop,
                    change_1d_pct=delta_pct,
                )
            )
            previous_close = row.close_price

        return FxHistoryResponse(
            pair=USD_COP_PAIR,
            source=YAHOO_SOURCE,
            latest_date=latest,
            points=points,
        )


def get_latest_usdcop() -> FxLatestResponse:
    result = get_usdcop_history(limit=1)
    return FxLatestResponse(
        pair=result.pair,
        source=result.source,
        latest_date=result.latest_date,
        point=result.points[-1],
    )
