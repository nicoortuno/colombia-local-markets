from __future__ import annotations

from datetime import date
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import httpx
import pandas as pd


SEN_BASE_URL = "https://www.banrep.gov.co/sites/default/files"


def build_sen_url(trade_date: date) -> str:
    """Build the official Banco de la República SEN daily file URL."""
    return (
        f"{SEN_BASE_URL}/"
        f"sen-{trade_date:%Y-%m-%d}.xls"
    )


def download_sen_file(trade_date: date) -> tuple[bytes, str]:
    """Download a daily SEN closing workbook from Banco de la República."""
    url = build_sen_url(trade_date)

    with httpx.Client(
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        response = client.get(url)
        response.raise_for_status()

    return response.content, url


def parse_tfit_maturity(security_id: str) -> date:
    """
    Decode the maturity date from a TFIT security identifier.

    Example:
        TFIT05270230 -> 2030-02-27

    The final six digits follow DDMMYY.
    """
    security_id = security_id.strip().upper()

    if not security_id.startswith("TFIT"):
        raise ValueError(
            f"Expected TFIT security, received {security_id!r}"
        )

    date_code = security_id[-6:]

    if not date_code.isdigit():
        raise ValueError(
            f"Could not decode maturity from {security_id!r}"
        )

    day = int(date_code[0:2])
    month = int(date_code[2:4])
    year = 2000 + int(date_code[4:6])

    return date(year, month, day)


def _normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""

    return " ".join(str(value).strip().split())


def _row_contains(
    frame: pd.DataFrame,
    row_index: int,
    target: str,
) -> bool:
    target = target.upper()

    return any(
        _normalize_text(value).upper() == target
        for value in frame.iloc[row_index]
    )


def _find_row(
    frame: pd.DataFrame,
    target: str,
    start: int = 0,
) -> int:
    for row_index in range(start, len(frame)):
        if _row_contains(frame, row_index, target):
            return row_index

    raise ValueError(
        f"Could not find row containing {target!r}"
    )


def _header_index_map(
    frame: pd.DataFrame,
    header_row: int,
) -> dict[str, int]:
    mapping: dict[str, int] = {}

    for column_index, value in enumerate(
        frame.iloc[header_row]
    ):
        name = _normalize_text(value)

        if name:
            mapping[name] = column_index

    return mapping


def _numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.strip()
        .replace(
            {
                "nan": None,
                "None": None,
                "": None,
            }
        ),
        errors="coerce",
    )


def _parse_sheet(
    raw: pd.DataFrame,
    trade_date: date,
    source_url: str | None,
) -> pd.DataFrame | None:
    """
    Locate the CONH -> PESOS -> TFIT section in one SEN sheet.
    """
    try:
        conh_row = _find_row(
            raw,
            "RUEDA CONH",
        )

        pesos_row = _find_row(
            raw,
            "PESOS",
            start=conh_row + 1,
        )

        header_row = _find_row(
            raw,
            "Especies",
            start=pesos_row + 1,
        )

    except ValueError:
        return None

    headers = _header_index_map(
        raw,
        header_row,
    )

    required_headers = [
        "Especies",
        "Nomin.Trans.(millones)",
        "Cant. Cierres",
        "Pre./tasa Apertura",
        "Equiv.Apertura",
        "Pre./tasa Minimo",
        "Equiv.Minima",
        "Pre./tasa Medio",
        "Equiv.Medio",
        "Pre./tasa Maximo",
        "Equiv.Maximo",
        "Pre./tasa Cierre",
        "Equiv.Cierre",
    ]

    missing = [
        column
        for column in required_headers
        if column not in headers
    ]

    if missing:
        raise ValueError(
            "SEN workbook is missing expected columns: "
            + ", ".join(missing)
        )

    security_column = headers["Especies"]

    total_row: int | None = None

    for row_index in range(
        header_row + 1,
        len(raw),
    ):
        security = _normalize_text(
            raw.iloc[row_index, security_column]
        ).upper()

        if security == "TOTAL":
            total_row = row_index
            break

    if total_row is None:
        raise ValueError(
            "Could not find TOTAL row for CONH/PESOS section"
        )

    data = raw.iloc[
        header_row + 1 : total_row
    ].copy()

    def column(name: str) -> pd.Series:
        return data.iloc[:, headers[name]]

    security_ids = (
        column("Especies")
        .astype(str)
        .str.strip()
        .str.upper()
    )

    output = pd.DataFrame(
        {
            "security_id": security_ids,
            "nominal_volume_cop_mn": _numeric(
                column("Nomin.Trans.(millones)")
            ),
            "trade_count": _numeric(
                column("Cant. Cierres")
            ),
            "open_price": _numeric(
                column("Pre./tasa Apertura")
            ),
            "open_yield": _numeric(
                column("Equiv.Apertura")
            ),
            "min_price": _numeric(
                column("Pre./tasa Minimo")
            ),
            "yield_at_min_price": _numeric(
                column("Equiv.Minima")
            ),
            "avg_price": _numeric(
                column("Pre./tasa Medio")
            ),
            "avg_yield": _numeric(
                column("Equiv.Medio")
            ),
            "max_price": _numeric(
                column("Pre./tasa Maximo")
            ),
            "yield_at_max_price": _numeric(
                column("Equiv.Maximo")
            ),
            "close_price": _numeric(
                column("Pre./tasa Cierre")
            ),
            "close_yield": _numeric(
                column("Equiv.Cierre")
            ),
        }
    )

    # Keep only nominal COP fixed-rate TES.
    output = output[
        output["security_id"].str.startswith(
            "TFIT",
            na=False,
        )
    ].copy()

    if output.empty:
        return None

    output.insert(
        0,
        "trade_date",
        trade_date,
    )

    output.insert(
        2,
        "maturity_date",
        output["security_id"].map(
            parse_tfit_maturity
        ),
    )

    output["trade_count"] = (
        output["trade_count"]
        .round()
        .astype("Int64")
    )

    output["source_url"] = source_url

    output = output.sort_values(
        "maturity_date"
    ).reset_index(drop=True)

    return output


def parse_sen_workbook(
    source: str | Path | bytes | BinaryIO,
    trade_date: date,
    source_url: str | None = None,
) -> pd.DataFrame:
    """
    Parse CONH/PESOS/TFIT cash-market data from a SEN workbook.
    """
    if isinstance(source, bytes):
        source = BytesIO(source)

    workbook = pd.ExcelFile(
        source,
        engine="xlrd",
    )

    results: list[pd.DataFrame] = []

    for sheet_name in workbook.sheet_names:
        raw = pd.read_excel(
            workbook,
            sheet_name=sheet_name,
            header=None,
        )

        parsed = _parse_sheet(
            raw=raw,
            trade_date=trade_date,
            source_url=source_url,
        )

        if parsed is not None:
            results.append(parsed)

    if not results:
        raise ValueError(
            "Could not locate a CONH/PESOS/TFIT section "
            "in the SEN workbook."
        )

    result = pd.concat(
        results,
        ignore_index=True,
    )

    result = result.drop_duplicates(
        subset=[
            "trade_date",
            "security_id",
        ],
        keep="first",
    )

    return result.sort_values(
        "maturity_date"
    ).reset_index(drop=True)


def fetch_tfit_market(
    trade_date: date,
) -> pd.DataFrame:
    """
    Download and parse one official SEN trading day.
    """
    content, url = download_sen_file(
        trade_date
    )

    return parse_sen_workbook(
        source=content,
        trade_date=trade_date,
        source_url=url,
    )
