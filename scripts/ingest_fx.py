"""USD/COP Yahoo daily OHLC backfill and incremental ingestion.

Run from backend/ using `uv run python ../scripts/ingest_fx.py ...`.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

# Ensure cross-directory scripts work even when the local editable install
# is not visible to uv's Python environment.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from colombia_markets.ingestion.fx import (  # noqa: E402
    download_yahoo_usdcop,
    FxDataError,
)
from colombia_markets.services.fx import (  # noqa: E402
    get_latest_fx_date,
    upsert_fx_daily_market,
)

INITIAL_START = date(2026, 7, 1)
OVERLAP_DAYS = 5
BOGOTA = ZoneInfo("America/Bogota")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest daily Yahoo USD/COP into Postgres")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--update", action="store_true", help="Resume from last stored date")
    mode.add_argument("--start", type=date.fromisoformat, help="Inclusive backfill start")
    parser.add_argument("--end", type=date.fromisoformat, help="Inclusive end (default: yesterday in Bogotá)")
    parser.add_argument(
        "--include-today",
        action="store_true",
        help="Opt into potentially incomplete/revisable Yahoo data for today",
    )
    return parser.parse_args()


def determine_window(
    *,
    update: bool,
    start_date: date | None,
    end_date: date | None,
    last_stored_date: date | None,
    today_bogota: date,
    include_today: bool = False,
) -> tuple[date, date]:
    max_allowed = today_bogota if include_today else today_bogota - timedelta(days=1)
    end = end_date or max_allowed
    if end > max_allowed:
        raise ValueError(
            f"End date {end} is not fully completed. Use --include-today to "
            "fetch today's revisable Yahoo observation. Future dates are not allowed."
        )

    if update:
        start = (
            last_stored_date - timedelta(days=OVERLAP_DAYS)
            if last_stored_date is not None
            else INITIAL_START
        )
    else:
        if start_date is None:
            raise ValueError("--start is required when not running --update")
        start = start_date
    return start, end


def main() -> None:
    args = parse_args()
    today = datetime.now(BOGOTA).date()
    last_stored = get_latest_fx_date() if args.update else None
    try:
        start, end = determine_window(
            update=args.update,
            start_date=args.start,
            end_date=args.end,
            last_stored_date=last_stored,
            today_bogota=today,
            include_today=args.include_today,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if start > end:
        if args.update:
            print(f"Up to date: last stored {last_stored}; no completed days to fetch.")
            return
        raise SystemExit("--start must be on or before --end")
    if args.include_today and end == today:
        print("NOTICE: Today's Yahoo OHLC may be incomplete; rerun tomorrow.")

    print(f"USD/COP (Yahoo COP=X): {start} through {end}, inclusive")
    if last_stored is not None:
        print(f"Previously stored through {last_stored}; rechecking last {OVERLAP_DAYS} days")

    try:
        records = download_yahoo_usdcop(start, end)
    except FxDataError as exc:
        raise SystemExit(f"Vendor data rejected; no changes written: {exc}") from exc
    except Exception as exc:
        raise SystemExit(f"Yahoo download failed; no changes written: {exc}") from exc

    if not records:
        print("No daily quotes returned (holiday/weekend or short empty range); nothing written.")
        return

    inserted_or_updated = upsert_fx_daily_market(records)
    print(
        f"Upserted {inserted_or_updated} USD/COP observations "
        f"({records[0]['trade_date']} → {records[-1]['trade_date']})."
    )
    print("The database unique constraint prevents duplicates on repeated runs.")


if __name__ == "__main__":
    main()
