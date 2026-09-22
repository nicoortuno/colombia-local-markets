from __future__ import annotations

from datetime import date
from decimal import Decimal

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from colombia_markets.db.models.tes import TesDailyMarket
from colombia_markets.db.session import SessionLocal
from colombia_markets.schemas.tes import (
    TesCurvePoint,
    TesCurveResponse,
)


TES_COLUMNS = [
    "trade_date",
    "security_id",
    "maturity_date",
    "nominal_volume_cop_mn",
    "trade_count",
    "open_price",
    "open_yield",
    "min_price",
    "yield_at_min_price",
    "avg_price",
    "avg_yield",
    "max_price",
    "yield_at_max_price",
    "close_price",
    "close_yield",
    "source_url",
]


def _to_decimal(value: object) -> Decimal | None:
    if pd.isna(value):
        return None

    return Decimal(str(value))


def _frame_to_records(frame: pd.DataFrame) -> list[dict]:
    records: list[dict] = []

    for row in frame.to_dict(orient="records"):
        records.append(
            {
                "trade_date": row["trade_date"],
                "security_id": row["security_id"],
                "maturity_date": row["maturity_date"],
                "nominal_volume_cop_mn": _to_decimal(
                    row["nominal_volume_cop_mn"]
                ),
                "trade_count": int(row["trade_count"]),
                "open_price": _to_decimal(row["open_price"]),
                "open_yield": _to_decimal(row["open_yield"]),
                "min_price": _to_decimal(row["min_price"]),
                "yield_at_min_price": _to_decimal(
                    row["yield_at_min_price"]
                ),
                "avg_price": _to_decimal(row["avg_price"]),
                "avg_yield": _to_decimal(row["avg_yield"]),
                "max_price": _to_decimal(row["max_price"]),
                "yield_at_max_price": _to_decimal(
                    row["yield_at_max_price"]
                ),
                "close_price": _to_decimal(row["close_price"]),
                "close_yield": _to_decimal(row["close_yield"]),
                "source_url": row.get("source_url"),
            }
        )

    return records


def upsert_tes_daily_market(frame: pd.DataFrame) -> int:
    """
    Insert or update daily TFIT observations.

    Uniqueness is defined by:
        trade_date + security_id
    """
    if frame.empty:
        return 0

    missing_columns = [
        column
        for column in TES_COLUMNS
        if column not in frame.columns
    ]

    if missing_columns:
        raise ValueError(
            "DataFrame is missing required columns: "
            + ", ".join(missing_columns)
        )

    records = _frame_to_records(frame)

    statement = insert(TesDailyMarket).values(records)

    update_columns = {
        column: getattr(statement.excluded, column)
        for column in TES_COLUMNS
        if column not in {
            "trade_date",
            "security_id",
        }
    }

    statement = statement.on_conflict_do_update(
        constraint="uq_tes_daily_market_date_security",
        set_=update_columns,
    )

    with SessionLocal() as session:
        session.execute(statement)
        session.commit()

    return len(records)


def _yield_map_for_date(
    session,
    reference_date: date | None,
) -> dict[str, float]:
    if reference_date is None:
        return {}

    rows = session.execute(
        select(
            TesDailyMarket.security_id,
            TesDailyMarket.close_yield,
        ).where(
            TesDailyMarket.trade_date == reference_date,
            TesDailyMarket.close_yield.is_not(None),
        )
    ).all()

    return {
        security_id: float(close_yield)
        for security_id, close_yield in rows
    }


def _bp_change(
    current_yield: Decimal | None,
    reference_yield: float | None,
) -> float | None:
    if current_yield is None or reference_yield is None:
        return None

    return round(
        (float(current_yield) - reference_yield) * 100,
        1,
    )


def get_tes_curve(
    trade_date: date | None = None,
) -> TesCurveResponse:
    with SessionLocal() as session:
        available_dates = list(
            session.scalars(
                select(TesDailyMarket.trade_date)
                .distinct()
                .order_by(TesDailyMarket.trade_date)
            ).all()
        )

        if not available_dates:
            raise ValueError("No TES market data is available.")

        latest_date = available_dates[-1]

        if trade_date is None:
            resolved_date = latest_date
        else:
            eligible_dates = [
                available_date
                for available_date in available_dates
                if available_date <= trade_date
            ]

            if not eligible_dates:
                raise ValueError(
                    f"No TES data found on or before {trade_date}"
                )

            resolved_date = eligible_dates[-1]

        date_index = available_dates.index(resolved_date)

        previous_date = (
            available_dates[date_index - 1]
            if date_index >= 1
            else None
        )

        five_day_date = (
            available_dates[date_index - 5]
            if date_index >= 5
            else None
        )

        next_date = (
            available_dates[date_index + 1]
            if date_index + 1 < len(available_dates)
            else None
        )

        one_day_yields = _yield_map_for_date(
            session,
            previous_date,
        )
        five_day_yields = _yield_map_for_date(
            session,
            five_day_date,
        )

        rows = session.scalars(
            select(TesDailyMarket)
            .where(
                TesDailyMarket.trade_date == resolved_date
            )
            .order_by(TesDailyMarket.maturity_date)
        ).all()

        if not rows:
            raise ValueError(
                f"No TES data found for {resolved_date}"
            )

        points = [
            TesCurvePoint(
                security_id=row.security_id,
                maturity_date=row.maturity_date,
                close_price=(
                    float(row.close_price)
                    if row.close_price is not None
                    else None
                ),
                close_yield=(
                    float(row.close_yield)
                    if row.close_yield is not None
                    else None
                ),
                change_1d_bp=_bp_change(
                    row.close_yield,
                    one_day_yields.get(row.security_id),
                ),
                change_5d_bp=_bp_change(
                    row.close_yield,
                    five_day_yields.get(row.security_id),
                ),
                nominal_volume_cop_mn=float(
                    row.nominal_volume_cop_mn
                ),
                trade_count=row.trade_count,
            )
            for row in rows
        ]

        return TesCurveResponse(
            trade_date=resolved_date,
            latest_date=latest_date,
            previous_date=previous_date,
            next_date=next_date,
            available_dates=available_dates,
            points=points,
        )
