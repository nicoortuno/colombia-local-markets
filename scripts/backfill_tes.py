from __future__ import annotations

import argparse
import time
from datetime import date, timedelta

import httpx

from colombia_markets.ingestion.tes_sen import fetch_tfit_market
from colombia_markets.services.rates import upsert_tes_daily_market


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Backfill Banco de la República SEN "
            "CONH/PESOS/TFIT market data."
        )
    )

    parser.add_argument(
        "--start",
        required=True,
        type=date.fromisoformat,
        help="Start date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--end",
        required=True,
        type=date.fromisoformat,
        help="End date in YYYY-MM-DD format.",
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=0.4,
        help=(
            "Delay in seconds between BanRep requests. "
            "Default: 0.4"
        ),
    )

    parser.add_argument(
        "--retries",
        type=int,
        default=3,
        help=(
            "Number of attempts for transient HTTP errors. "
            "Default: 3"
        ),
    )

    return parser.parse_args()


def iter_dates(
    start_date: date,
    end_date: date,
):
    current_date = start_date

    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)


def fetch_with_retry(
    trade_date: date,
    retries: int,
):
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            return fetch_tfit_market(
                trade_date=trade_date
            )

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code

            # Missing SEN files are normal for Colombian
            # holidays and other non-trading dates.
            if status_code in {404, 410}:
                raise

            # Retry temporary server/rate-limit errors.
            if (
                status_code == 429
                or status_code >= 500
            ):
                last_error = exc

                if attempt < retries:
                    time.sleep(
                        1.5 * attempt
                    )
                    continue

            raise

        except httpx.RequestError as exc:
            last_error = exc

            if attempt < retries:
                time.sleep(
                    1.5 * attempt
                )
                continue

            raise

    if last_error is not None:
        raise last_error

    raise RuntimeError(
        f"Unable to fetch {trade_date}"
    )


def main() -> None:
    args = parse_args()

    if args.end < args.start:
        raise SystemExit(
            "--end must be on or after --start"
        )

    successful_days = 0
    unavailable_days = 0
    weekend_days = 0
    failed_days = 0
    total_rows = 0

    failures: list[
        tuple[date, str]
    ] = []

    print()
    print(
        "TES SEN BACKFILL"
    )
    print(
        f"{args.start} -> {args.end}"
    )
    print(
        "-" * 64
    )

    for trade_date in iter_dates(
        args.start,
        args.end,
    ):
        # Saturday = 5, Sunday = 6
        if trade_date.weekday() >= 5:
            weekend_days += 1
            continue

        try:
            frame = fetch_with_retry(
                trade_date=trade_date,
                retries=args.retries,
            )

            row_count = (
                upsert_tes_daily_market(
                    frame
                )
            )

            successful_days += 1
            total_rows += row_count

            print(
                f"{trade_date}  ✓  "
                f"{row_count:>2} securities"
            )

        except httpx.HTTPStatusError as exc:
            status_code = (
                exc.response.status_code
            )

            if status_code in {404, 410}:
                unavailable_days += 1

                print(
                    f"{trade_date}  -  "
                    "no SEN file"
                )

            else:
                failed_days += 1

                message = (
                    f"HTTP {status_code}"
                )

                failures.append(
                    (
                        trade_date,
                        message,
                    )
                )

                print(
                    f"{trade_date}  ✗  "
                    f"{message}"
                )

        except Exception as exc:
            failed_days += 1

            message = (
                f"{type(exc).__name__}: "
                f"{exc}"
            )

            failures.append(
                (
                    trade_date,
                    message,
                )
            )

            print(
                f"{trade_date}  ✗  "
                f"{message}"
            )

        time.sleep(
            max(args.delay, 0)
        )

    print()
    print(
        "-" * 64
    )
    print("BACKFILL COMPLETE")
    print()

    print(
        f"Successful trading days : "
        f"{successful_days}"
    )

    print(
        f"Unavailable weekdays    : "
        f"{unavailable_days}"
    )

    print(
        f"Weekend days skipped    : "
        f"{weekend_days}"
    )

    print(
        f"Failed days             : "
        f"{failed_days}"
    )

    print(
        f"Rows upserted           : "
        f"{total_rows}"
    )

    if failures:
        print()
        print("FAILURES")

        for failed_date, message in failures:
            print(
                f"  {failed_date}: "
                f"{message}"
            )

        raise SystemExit(1)


if __name__ == "__main__":
    main()
