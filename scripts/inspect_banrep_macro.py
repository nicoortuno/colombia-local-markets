from __future__ import annotations

import argparse
import math
import ssl
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import truststore


BANREP_URL = (
    "https://suameca.banrep.gov.co/"
    "buscador-de-series/rest/buscadorSeriesRestService/"
    "consultaDatosSeries"
)

BANREP_REFERER = (
    "https://suameca.banrep.gov.co/"
    "descarga-multiple-de-datos/consolidado"
)

BOGOTA = ZoneInfo("America/Bogota")


@dataclass(frozen=True)
class SeriesConfig:
    key: str
    id: int
    periodicity_id: int
    expected_name: str
    frequency: str


SERIES: dict[str, SeriesConfig] = {
    "policy_rate": SeriesConfig(
        key="policy_rate",
        id=59,
        periodicity_id=1,
        expected_name="Tasa de política monetaria",
        frequency="daily_calendar",
    ),
    "ibr_overnight": SeriesConfig(
        key="ibr_overnight",
        id=15324,
        periodicity_id=1,
        expected_name=(
            "Indicador Bancario de Referencia "
            "(IBR) overnight, efectiva"
        ),
        frequency="daily_business",
    ),
    "headline_inflation": SeriesConfig(
        key="headline_inflation",
        id=15270,
        periodicity_id=9,
        expected_name="Inflación total anual",
        frequency="monthly",
    ),
    "core_inflation": SeriesConfig(
        key="core_inflation",
        id=15390,
        periodicity_id=9,
        expected_name=(
            "Inflación sin alimentos ni regulados"
        ),
        frequency="monthly",
    ),
    "real_gdp": SeriesConfig(
        key="real_gdp",
        id=15154,
        periodicity_id=12,
        expected_name=(
            "Producto Interno Bruto (PIB) real, "
            "Trimestral, base: 2015"
        ),
        frequency="quarterly",
    ),
    "unemployment": SeriesConfig(
        key="unemployment",
        id=15312,
        periodicity_id=9,
        expected_name=(
            "Tasa de desempleo - total nacional"
        ),
        frequency="monthly",
    ),
    "current_account_gdp": SeriesConfig(
        key="current_account_gdp",
        id=15290,
        periodicity_id=12,
        expected_name=(
            "Cuenta corriente, porcentaje del PIB, "
            "trimestral"
        ),
        frequency="quarterly",
    ),
    "net_reserves": SeriesConfig(
        key="net_reserves",
        id=15051,
        periodicity_id=9,
        expected_name=(
            "Reservas internacionales netas"
        ),
        frequency="monthly",
    ),
}


def yyyymmdd(value: date) -> int:
    return int(value.strftime("%Y%m%d"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate official Banco de la República "
            "macro series."
        )
    )

    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        default=date(2025, 1, 1),
        help=(
            "Requested history start in YYYY-MM-DD "
            "format. Default: 2025-01-01."
        ),
    )

    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=date.today(),
        help=(
            "Requested end date in YYYY-MM-DD format. "
            "Default: today."
        ),
    )

    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
    )

    return parser.parse_args()


def build_ssl_context() -> ssl.SSLContext:
    return truststore.SSLContext(
        ssl.PROTOCOL_TLS_CLIENT
    )


def fetch_all_series(
    start: date,
    end: date,
    timeout: float,
) -> list[dict[str, Any]]:
    payload = {
        "series": [
            {
                "idSerie": config.id,
                "idPeriodicidades": [
                    config.periodicity_id
                ],
            }
            for config in SERIES.values()
        ],
        "fechaInicio": yyyymmdd(start),
        "fechaFin": yyyymmdd(end),
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://suameca.banrep.gov.co",
        "Referer": BANREP_REFERER,
    }

    ssl_context = build_ssl_context()

    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=headers,
        verify=ssl_context,
    ) as client:
        response = client.post(
            BANREP_URL,
            json=payload,
        )

    print()
    print(f"POST {BANREP_URL}")
    print(f"HTTP {response.status_code}")
    print(
        "Content-Type:",
        response.headers.get(
            "content-type",
            "",
        ),
    )
    print(
        "Downloaded:",
        f"{len(response.content):,} bytes",
    )

    response.raise_for_status()

    try:
        body = response.json()
    except ValueError as exc:
        preview = response.text[:500]

        raise RuntimeError(
            "BanRep did not return JSON.\n"
            "First 500 characters:\n"
            f"{preview}"
        ) from exc

    if not isinstance(body, list):
        raise RuntimeError(
            "Unexpected BanRep response type: "
            f"{type(body).__name__}"
        )

    return body


def timestamp_to_bogota_date(
    timestamp_ms: int | float,
) -> date:
    return (
        datetime.fromtimestamp(
            timestamp_ms / 1000,
            tz=timezone.utc,
        )
        .astimezone(BOGOTA)
        .date()
    )


def extract_observations(
    series: dict[str, Any],
) -> list[tuple[date, float]]:
    observations: list[
        tuple[date, float]
    ] = []

    seen_dates: set[date] = set()

    for row in series.get("data", []):
        if (
            not isinstance(row, list)
            or len(row) != 2
        ):
            continue

        timestamp_ms, raw_value = row

        if (
            timestamp_ms is None
            or raw_value is None
        ):
            continue

        observed_date = (
            timestamp_to_bogota_date(
                timestamp_ms
            )
        )

        value = float(raw_value)

        if not math.isfinite(value):
            raise RuntimeError(
                f"Non-finite value for "
                f"{series.get('nombre')}: "
                f"{raw_value}"
            )

        if observed_date in seen_dates:
            raise RuntimeError(
                "Duplicate date in "
                f"{series.get('nombre')}: "
                f"{observed_date}"
            )

        seen_dates.add(observed_date)

        observations.append(
            (observed_date, value)
        )

    observations.sort(
        key=lambda item: item[0]
    )

    return observations


def validate_response(
    body: list[dict[str, Any]],
) -> dict[
    str,
    tuple[
        dict[str, Any],
        list[tuple[date, float]],
    ],
]:
    validated: dict[
        str,
        tuple[
            dict[str, Any],
            list[tuple[date, float]],
        ],
    ] = {}

    print()
    print("=" * 88)
    print("BANREP SERIES VALIDATION")
    print("=" * 88)

    for key, config in SERIES.items():
        matches = [
            item
            for item in body
            if item.get("id") == config.id
            and item.get("idPeriodicidad")
            == config.periodicity_id
        ]

        if len(matches) != 1:
            returned = [
                (
                    item.get("id"),
                    item.get("idPeriodicidad"),
                    item.get("nombre"),
                )
                for item in body
            ]

            raise RuntimeError(
                f"{key}: expected exactly one "
                f"matching result, found "
                f"{len(matches)}.\n"
                f"Returned series: {returned}"
            )

        series = matches[0]

        actual_name = series.get("nombre")

        if actual_name != config.expected_name:
            raise RuntimeError(
                f"{key}: unexpected name.\n"
                f"Expected: "
                f"{config.expected_name!r}\n"
                f"Actual:   "
                f"{actual_name!r}"
            )

        observations = (
            extract_observations(series)
        )

        if not observations:
            raise RuntimeError(
                f"{key}: BanRep returned "
                "no observations."
            )

        validated[key] = (
            series,
            observations,
        )

        latest_date, latest_value = (
            observations[-1]
        )

        print()
        print(
            f"[OK] {key}"
        )
        print(
            f"     ID: {config.id}"
        )
        print(
            "     Name:",
            actual_name,
        )
        print(
            "     Periodicity:",
            series.get(
                "descripcionPeriodicidad"
            ),
            (
                f"(id="
                f"{series.get('idPeriodicidad')}"
                f")"
            ),
        )
        print(
            "     Unit:",
            series.get("unidad"),
        )
        print(
            "     Source:",
            (
                series.get("fuenteCorta")
                or series.get("fuente")
            ),
        )
        print(
            "     Observations:",
            len(observations),
        )
        print(
            "     Range:",
            observations[0][0],
            "→",
            latest_date,
        )
        print(
            "     Latest value:",
            latest_value,
        )

    return validated


def latest(
    validated: dict[
        str,
        tuple[
            dict[str, Any],
            list[tuple[date, float]],
        ],
    ],
    key: str,
) -> tuple[date, float]:
    return validated[key][1][-1]


def calculate_gdp_yoy(
    observations: list[
        tuple[date, float]
    ],
) -> tuple[
    date,
    float,
    date,
    float,
    float,
]:
    if len(observations) < 5:
        raise RuntimeError(
            "Need at least five quarterly GDP "
            "observations to calculate YoY growth."
        )

    latest_date, latest_level = (
        observations[-1]
    )

    comparison_date, comparison_level = (
        observations[-5]
    )

    yoy = (
        latest_level
        / comparison_level
        - 1
    ) * 100

    return (
        latest_date,
        latest_level,
        comparison_date,
        comparison_level,
        yoy,
    )


def format_pct(
    value: float,
    decimals: int = 2,
) -> str:
    return f"{value:.{decimals}f}%"


def format_signed_pct(
    value: float,
    decimals: int = 2,
) -> str:
    return f"{value:+.{decimals}f}%"


def format_bp(
    value: float,
    decimals: int = 1,
) -> str:
    return f"{value:+.{decimals}f} bp"


def quarter_label(value: date) -> str:
    quarter = (
        (value.month - 1) // 3
    ) + 1

    return f"{value.year} Q{quarter}"


def month_label(value: date) -> str:
    return value.strftime("%Y-%m")


def print_snapshot(
    validated: dict[
        str,
        tuple[
            dict[str, Any],
            list[tuple[date, float]],
        ],
    ],
) -> None:
    policy_date, policy = latest(
        validated,
        "policy_rate",
    )

    ibr_date, ibr = latest(
        validated,
        "ibr_overnight",
    )

    headline_date, headline = latest(
        validated,
        "headline_inflation",
    )

    core_date, core = latest(
        validated,
        "core_inflation",
    )

    unemployment_date, unemployment = (
        latest(
            validated,
            "unemployment",
        )
    )

    ca_date, current_account = latest(
        validated,
        "current_account_gdp",
    )

    reserves_date, reserves_mn = latest(
        validated,
        "net_reserves",
    )

    (
        gdp_date,
        gdp_level,
        gdp_prior_date,
        gdp_prior_level,
        gdp_yoy,
    ) = calculate_gdp_yoy(
        validated["real_gdp"][1]
    )

    ibr_policy_bp = (
        ibr - policy
    ) * 100

    reserves_bn = (
        reserves_mn / 1000
    )

    print()
    print("=" * 88)
    print("COLOMBIA MACRO SNAPSHOT")
    print("=" * 88)

    print(
        f"{'Policy rate':30}"
        f"{format_pct(policy, 3):>14}"
        f"   {policy_date}"
    )

    print(
        f"{'IBR overnight effective':30}"
        f"{format_pct(ibr, 3):>14}"
        f"   {ibr_date}"
    )

    print(
        f"{'IBR - policy spread':30}"
        f"{format_bp(ibr_policy_bp):>14}"
    )

    print("-" * 88)

    print(
        f"{'Headline inflation YoY':30}"
        f"{format_pct(headline, 2):>14}"
        f"   {month_label(headline_date)}"
    )

    print(
        f"{'Core inflation':30}"
        f"{format_pct(core, 2):>14}"
        f"   {month_label(core_date)}"
    )

    print(
        f"{'Unemployment':30}"
        f"{format_pct(unemployment, 2):>14}"
        f"   {month_label(unemployment_date)}"
    )

    print("-" * 88)

    print(
        f"{'Real GDP YoY':30}"
        f"{format_signed_pct(gdp_yoy, 2):>14}"
        f"   {quarter_label(gdp_date)}"
    )

    print(
        f"{'Current account / GDP':30}"
        f"{format_signed_pct(current_account, 2):>14}"
        f"   {quarter_label(ca_date)}"
    )

    print(
        f"{'Net international reserves':30}"
        f"{('$' + format(reserves_bn, '.2f') + 'bn'):>14}"
        f"   {month_label(reserves_date)}"
    )

    print()
    print("GDP CALCULATION CHECK")
    print("-" * 88)

    print(
        f"Latest quarter:      "
        f"{quarter_label(gdp_date)}"
        f" = {gdp_level:,.2f} "
        "COP bn"
    )

    print(
        f"Prior-year quarter:  "
        f"{quarter_label(gdp_prior_date)}"
        f" = {gdp_prior_level:,.2f} "
        "COP bn"
    )

    print(
        "Calculated YoY:      "
        f"{gdp_yoy:+.4f}%"
    )


def check_freshness(
    validated: dict[
        str,
        tuple[
            dict[str, Any],
            list[tuple[date, float]],
        ],
    ],
    as_of: date,
) -> None:
    thresholds = {
        "policy_rate": 7,
        "ibr_overnight": 10,
        "headline_inflation": 70,
        "core_inflation": 70,
        "real_gdp": 150,
        "unemployment": 70,
        "current_account_gdp": 180,
        "net_reserves": 70,
    }

    print()
    print("=" * 88)
    print("FRESHNESS CHECK")
    print("=" * 88)

    for key in SERIES:
        latest_date = (
            validated[key][1][-1][0]
        )

        age = (
            as_of - latest_date
        ).days

        max_age = thresholds[key]

        status = (
            "OK"
            if age <= max_age
            else "STALE?"
        )

        print(
            f"{status:7} "
            f"{key:24} "
            f"latest={latest_date} "
            f"age={age:3} days "
            f"threshold={max_age}"
        )


def main() -> None:
    args = parse_args()

    if args.end < args.start:
        raise SystemExit(
            "--end must be on or "
            "after --start"
        )

    # GDP YoY requires the same quarter
    # from the prior year. Fetch enough
    # history even if the user requests
    # a short validation range.
    minimum_history_start = (
        args.end - timedelta(days=550)
    )

    fetch_start = min(
        args.start,
        minimum_history_start,
    )

    print(
        "Requested range:",
        args.start,
        "→",
        args.end,
    )

    print(
        "API fetch range:",
        fetch_start,
        "→",
        args.end,
    )

    body = fetch_all_series(
        start=fetch_start,
        end=args.end,
        timeout=args.timeout,
    )

    validated = validate_response(
        body
    )

    print_snapshot(
        validated
    )

    check_freshness(
        validated,
        as_of=args.end,
    )

    print()
    print("=" * 88)
    print(
        "ALL 8 BANREP MACRO SERIES "
        "VALIDATED SUCCESSFULLY"
    )
    print("=" * 88)


if __name__ == "__main__":
    main()
