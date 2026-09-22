from datetime import date
from pathlib import Path
import sys

from colombia_markets.ingestion.tes_sen import parse_sen_workbook


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python inspect_tes.py /path/to/sen-YYYY-MM-DD.xls"
        )

    file_path = Path(sys.argv[1])

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

    print()
    print(f"Trading date: {trade_date}")
    print(f"TFIT securities: {len(frame)}")
    print()

    print(
        frame[
            [
                "security_id",
                "maturity_date",
                "close_price",
                "close_yield",
                "nominal_volume_cop_mn",
                "trade_count",
            ]
        ].to_string(index=False)
    )


if __name__ == "__main__":
    main()
