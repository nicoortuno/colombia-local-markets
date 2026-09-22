from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

from colombia_markets.ingestion.tes_sen import (
    fetch_tfit_market,
    parse_sen_workbook,
)
from colombia_markets.services.rates import (
    upsert_tes_daily_market,
)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Usage:\n"
            "  python ingest_tes.py YYYY-MM-DD\n"
            "  python ingest_tes.py /path/to/sen-YYYY-MM-DD.xls"
        )

    argument = sys.argv[1]

    if argument.endswith(".xls"):
        file_path = Path(argument)

        if not file_path.exists():
            raise SystemExit(
                f"File not found: {file_path}"
            )

        trade_date = date.fromisoformat(
            file_path.stem.replace("sen-", "")
        )

        frame = parse_sen_workbook(
            source=file_path,
            trade_date=trade_date,
            source_url=None,
        )

    else:
        trade_date = date.fromisoformat(argument)

        frame = fetch_tfit_market(
            trade_date=trade_date,
        )

    row_count = upsert_tes_daily_market(frame)

    print(
        f"Upserted {row_count} TES rows "
        f"for {trade_date}"
    )


if __name__ == "__main__":
    main()
