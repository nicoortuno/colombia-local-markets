"""BanRep macro backfill and revision-aware incremental ingestion.

Run from backend/ using:
    uv run python ../scripts/ingest_macro.py --start 2015-01-01 --end 2026-09-23
    uv run python ../scripts/ingest_macro.py --update
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
import sys
from zoneinfo import ZoneInfo

# Keep scripts runnable even if the editable package is temporarily unavailable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "src"))

from colombia_markets.ingestion.macro import (  # noqa: E402
    MacroDataError,
    SERIES,
    download_banrep_macro,
)
from colombia_markets.services.macro import (  # noqa: E402
    get_latest_macro_dates,
    get_macro_row_counts,
    upsert_macro_observations,
)

BOGOTA = ZoneInfo("America/Bogota")
INITIAL_START = date(2015, 1, 1)

# Re-fetch enough history to absorb normal official revisions without needing
# a full historical download every day.
REVISION_DAYS = {
    "daily": 14,
    "monthly": 240,      # ~8 months
    "quarterly": 800,    # >8 quarters
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Ingest validated BanRep macro series into Postgres"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--update",
        action="store_true",
        help="Re-fetch revision windows and upsert the latest official data",
    )
    mode.add_argument(
        "--start",
        type=date.fromisoformat,
        help="Inclusive historical backfill start (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        help="Inclusive end date (default: today in Bogotá)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="HTTP timeout in seconds (default: 60)",
    )
    return parser.parse_args()


def _group_keys(group: str) -> list[str]:
    return [config.key for config in SERIES.values() if config.update_group == group]


def _update_start_for_group(
    group: str,
    latest_dates: dict[str, date],
) -> date:
    starts: list[date] = []
    overlap = REVISION_DAYS[group]
    for key in _group_keys(group):
        latest = latest_dates.get(key)
        starts.append(
            latest - timedelta(days=overlap)
            if latest is not None
            else INITIAL_START
        )
    return min(starts)


def _print_batch_summary(records: list[dict]) -> None:
    counts = Counter(row["series_key"] for row in records)
    for key in SERIES:
        print(f"  {key:24} {counts.get(key, 0):>5} observations")


def main() -> None:
    args = parse_args()
    today = datetime.now(BOGOTA).date()
    end = args.end or today

    if end > today:
        raise SystemExit(f"--end cannot be in the future (Bogotá today is {today})")

    all_records: list[dict] = []

    try:
        if args.update:
            latest_dates = get_latest_macro_dates()
            print(f"BanRep macro update through {end}")

            for group in ("daily", "monthly", "quarterly"):
                keys = _group_keys(group)
                start = _update_start_for_group(group, latest_dates)
                if start > end:
                    print(f"{group.capitalize():9}: no range to fetch")
                    continue

                print(
                    f"{group.capitalize():9}: {start} → {end} "
                    f"({', '.join(keys)})"
                )
                records = download_banrep_macro(
                    start,
                    end,
                    series_keys=keys,
                    timeout=args.timeout,
                )
                all_records.extend(records)
        else:
            start = args.start
            if start is None:
                raise SystemExit("--start is required for historical backfill")
            if start > end:
                raise SystemExit("--start must be on or before --end")

            print(f"BanRep macro backfill: {start} → {end}")
            all_records = download_banrep_macro(
                start,
                end,
                timeout=args.timeout,
            )

    except MacroDataError as exc:
        raise SystemExit(f"BanRep data rejected; no changes written: {exc}") from exc
    except Exception as exc:
        raise SystemExit(f"Macro ingestion failed; no changes written: {exc}") from exc

    if not all_records:
        print("No observations returned; nothing written.")
        return

    # A grouped update could theoretically overlap only if configuration changes;
    # guard against conflicting duplicates before reaching PostgreSQL.
    by_key_date: dict[tuple[str, date], dict] = {}
    for record in all_records:
        identity = (record["series_key"], record["observation_date"])
        previous = by_key_date.get(identity)
        if previous is not None and previous != record:
            raise SystemExit(f"Conflicting duplicate macro observation: {identity}")
        by_key_date[identity] = record
    records = sorted(
        by_key_date.values(),
        key=lambda row: (row["series_key"], row["observation_date"]),
    )

    print("\nDownloaded / normalized:")
    _print_batch_summary(records)

    written = upsert_macro_observations(records)
    print(f"\nUpserted {written} macro observations.")
    print("Unique (series_key, observation_date) prevents duplicate rows.")

    counts = get_macro_row_counts()
    print("\nRows currently stored:")
    for key in SERIES:
        print(f"  {key:24} {counts.get(key, 0):>5}")


if __name__ == "__main__":
    main()
