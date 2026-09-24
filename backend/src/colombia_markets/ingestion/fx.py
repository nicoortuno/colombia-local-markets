"""Daily Yahoo USD/COP OHLC downloads; vendor session dates are preserved."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

import pandas as pd

USD_COP_TICKER = "COP=X"
USD_COP_PAIR = "USD/COP"
YAHOO_SOURCE = "yahoo_finance"


class FxDataError(ValueError):
    """Invalid or unexpectedly missing vendor market data."""


def _positive_price(value: object, column: str, day: date) -> Decimal:
    if pd.isna(value):
        raise FxDataError(f"{day}: missing {column} price")
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise FxDataError(f"{day}: invalid {column} price {value!r}") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise FxDataError(f"{day}: invalid {column} price {value!r}")
    return parsed.quantize(Decimal("0.000001"))


def normalize_yahoo_history(
    history: pd.DataFrame,
    start_date: date,
    end_date: date,
) -> list[dict]:
    """Produce normalized records, retaining Yahoo's date without TZ conversion.

    The Yahoo index may show midnight +01:00. Converting that instant to
    America/Bogota would incorrectly put the vendor's session on the previous day.
    """
    if history.empty:
        return []

    required = {"Open", "High", "Low", "Close"}
    missing = required.difference(history.columns)
    if missing:
        raise FxDataError(f"Yahoo history missing columns: {', '.join(sorted(missing))}")

    by_day: dict[date, dict] = {}
    for timestamp, row in history.iterrows():
        try:
            # DO NOT tz_convert('America/Bogota'): Yahoo's index is a session label.
            day = pd.Timestamp(timestamp).date()
        except (TypeError, ValueError) as exc:
            raise FxDataError(f"Unrecognized Yahoo session date: {timestamp!r}") from exc
        if not start_date <= day <= end_date:
            continue

        open_price = _positive_price(row["Open"], "open", day)
        high_price = _positive_price(row["High"], "high", day)
        low_price = _positive_price(row["Low"], "low", day)
        close_price = _positive_price(row["Close"], "close", day)

        if high_price < low_price:
            raise FxDataError(f"{day}: high is below low")

        # Do not enforce close inside high/low. Yahoo's FX OHLC can reflect
        # differing quote/roll conventions; do not mistake it for SET-FX OHLC.
        record = {
            "trade_date": day,
            "pair": USD_COP_PAIR,
            "source": YAHOO_SOURCE,
            "open_price": open_price,
            "high_price": high_price,
            "low_price": low_price,
            "close_price": close_price,
        }
        if day in by_day and by_day[day] != record:
            raise FxDataError(f"Conflicting USD/COP records for {day}")
        by_day[day] = record

    return [by_day[day] for day in sorted(by_day)]


def download_yahoo_usdcop(start_date: date, end_date: date) -> list[dict]:
    """Download an inclusive session-date interval using Yahoo's exclusive end."""
    if end_date < start_date:
        raise ValueError("end_date must not precede start_date")

    # Import lazily so pure validation tests do not require a network client.
    import yfinance as yf

    history = yf.Ticker(USD_COP_TICKER).history(
        start=start_date.isoformat(),
        end=(end_date + timedelta(days=1)).isoformat(),
        interval="1d",
        auto_adjust=False,
        actions=False,
    )
    records = normalize_yahoo_history(history, start_date, end_date)

    weekdays = sum(
        (start_date + timedelta(days=n)).weekday() < 5
        for n in range((end_date - start_date).days + 1)
    )
    if not records and weekdays >= 3:
        raise FxDataError(
            "Yahoo returned no observations for a range containing at least "
            "three weekdays. This could be a source outage or throttling; no "
            "database changes were made."
        )
    return records
