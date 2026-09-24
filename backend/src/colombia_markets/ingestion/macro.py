"""Official macro-series downloads from Banco de la República SUAMECA."""

from __future__ import annotations

import math
import ssl
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable
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
BANREP_PROVIDER = "banrep_suameca"
BOGOTA = ZoneInfo("America/Bogota")


class MacroDataError(ValueError):
    """Invalid, incomplete, or structurally unexpected official macro data."""


@dataclass(frozen=True)
class MacroSeriesConfig:
    key: str
    id: int
    periodicity_id: int
    expected_name: str
    frequency: str
    update_group: str


SERIES: dict[str, MacroSeriesConfig] = {
    "policy_rate": MacroSeriesConfig(
        key="policy_rate",
        id=59,
        periodicity_id=1,
        expected_name="Tasa de política monetaria",
        frequency="daily_calendar",
        update_group="daily",
    ),
    "ibr_overnight": MacroSeriesConfig(
        key="ibr_overnight",
        id=15324,
        periodicity_id=1,
        expected_name=(
            "Indicador Bancario de Referencia (IBR) overnight, efectiva"
        ),
        frequency="daily_business",
        update_group="daily",
    ),
    "headline_inflation": MacroSeriesConfig(
        key="headline_inflation",
        id=15270,
        periodicity_id=9,
        expected_name="Inflación total anual",
        frequency="monthly",
        update_group="monthly",
    ),
    "core_inflation": MacroSeriesConfig(
        key="core_inflation",
        id=15390,
        periodicity_id=9,
        expected_name="Inflación sin alimentos ni regulados",
        frequency="monthly",
        update_group="monthly",
    ),
    "real_gdp": MacroSeriesConfig(
        key="real_gdp",
        id=15154,
        periodicity_id=12,
        expected_name=(
            "Producto Interno Bruto (PIB) real, Trimestral, base: 2015"
        ),
        frequency="quarterly",
        update_group="quarterly",
    ),
    "unemployment": MacroSeriesConfig(
        key="unemployment",
        id=15312,
        periodicity_id=9,
        expected_name="Tasa de desempleo - total nacional",
        frequency="monthly",
        update_group="monthly",
    ),
    "current_account_gdp": MacroSeriesConfig(
        key="current_account_gdp",
        id=15290,
        periodicity_id=12,
        expected_name="Cuenta corriente, porcentaje del PIB, trimestral",
        frequency="quarterly",
        update_group="quarterly",
    ),
    "net_reserves": MacroSeriesConfig(
        key="net_reserves",
        id=15051,
        periodicity_id=9,
        expected_name="Reservas internacionales netas",
        frequency="monthly",
        update_group="monthly",
    ),
}


def yyyymmdd(value: date) -> int:
    return int(value.strftime("%Y%m%d"))


def _ssl_context() -> ssl.SSLContext:
    # Use the macOS/native trust store. This is necessary for BanRep's current
    # certificate chain in the user's uv-managed Python environment.
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _configs(series_keys: Iterable[str] | None) -> list[MacroSeriesConfig]:
    if series_keys is None:
        return list(SERIES.values())

    keys = list(series_keys)
    unknown = sorted(set(keys).difference(SERIES))
    if unknown:
        raise ValueError(f"Unknown macro series key(s): {', '.join(unknown)}")
    return [SERIES[key] for key in keys]


def _timestamp_to_bogota_date(timestamp_ms: int | float) -> date:
    return (
        datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        .astimezone(BOGOTA)
        .date()
    )


def _decimal_value(value: object, *, series_key: str, observed_date: date) -> Decimal:
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise MacroDataError(
            f"{series_key} {observed_date}: invalid numeric value {value!r}"
        ) from exc
    if not parsed.is_finite() or not math.isfinite(float(parsed)):
        raise MacroDataError(
            f"{series_key} {observed_date}: non-finite value {value!r}"
        )
    return parsed.quantize(Decimal("0.00000001"))


def _clean_source(series: dict[str, Any]) -> str:
    source = series.get("fuenteCorta") or series.get("fuente")
    if not isinstance(source, str) or not source.strip():
        raise MacroDataError(f"{series.get('nombre')!r}: missing source metadata")
    source = source.strip()
    if source.lower().startswith("fuente:"):
        source = source.split(":", 1)[1].strip()
    return source


def normalize_banrep_response(
    body: object,
    *,
    start_date: date,
    end_date: date,
    series_keys: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Validate a SUAMECA response and normalize it to DB-ready records."""
    if end_date < start_date:
        raise ValueError("end_date must not precede start_date")
    if not isinstance(body, list):
        raise MacroDataError(
            f"Unexpected BanRep response type: {type(body).__name__}"
        )

    configs = _configs(series_keys)
    records: list[dict[str, Any]] = []

    for config in configs:
        matches = [
            item
            for item in body
            if isinstance(item, dict)
            and item.get("id") == config.id
            and item.get("idPeriodicidad") == config.periodicity_id
        ]
        if len(matches) != 1:
            returned = [
                (item.get("id"), item.get("idPeriodicidad"), item.get("nombre"))
                for item in body
                if isinstance(item, dict)
            ]
            raise MacroDataError(
                f"{config.key}: expected one result for series {config.id} / "
                f"periodicity {config.periodicity_id}, found {len(matches)}. "
                f"Returned: {returned}"
            )

        series = matches[0]
        if series.get("nombre") != config.expected_name:
            raise MacroDataError(
                f"{config.key}: expected name {config.expected_name!r}, "
                f"got {series.get('nombre')!r}"
            )

        unit = series.get("unidad")
        if not isinstance(unit, str) or not unit.strip():
            raise MacroDataError(f"{config.key}: missing unit metadata")
        source = _clean_source(series)

        raw_data = series.get("data", [])
        if raw_data is None:
            raw_data = []
        if not isinstance(raw_data, list):
            raise MacroDataError(f"{config.key}: data is not a list")

        seen_dates: set[date] = set()
        for row in raw_data:
            if not isinstance(row, list) or len(row) != 2:
                raise MacroDataError(f"{config.key}: malformed observation {row!r}")
            timestamp_ms, raw_value = row
            if timestamp_ms is None or raw_value is None:
                raise MacroDataError(f"{config.key}: null observation {row!r}")

            try:
                observed_date = _timestamp_to_bogota_date(timestamp_ms)
            except (TypeError, ValueError, OSError, OverflowError) as exc:
                raise MacroDataError(
                    f"{config.key}: invalid timestamp {timestamp_ms!r}"
                ) from exc

            # The endpoint honors the requested range, but filter defensively.
            if not start_date <= observed_date <= end_date:
                continue
            if observed_date in seen_dates:
                raise MacroDataError(
                    f"{config.key}: duplicate observation date {observed_date}"
                )
            seen_dates.add(observed_date)

            records.append(
                {
                    "series_key": config.key,
                    "series_name": config.expected_name,
                    "observation_date": observed_date,
                    "value": _decimal_value(
                        raw_value,
                        series_key=config.key,
                        observed_date=observed_date,
                    ),
                    "source_series_id": config.id,
                    "periodicity_id": config.periodicity_id,
                    "frequency": config.frequency,
                    "unit": unit.strip(),
                    "source": source,
                    "provider": BANREP_PROVIDER,
                }
            )

    records.sort(key=lambda row: (row["series_key"], row["observation_date"]))
    return records


def download_banrep_macro(
    start_date: date,
    end_date: date,
    *,
    series_keys: Iterable[str] | None = None,
    timeout: float = 60.0,
) -> list[dict[str, Any]]:
    """Download and normalize an inclusive date range from BanRep SUAMECA."""
    if end_date < start_date:
        raise ValueError("end_date must not precede start_date")

    configs = _configs(series_keys)
    if not configs:
        return []

    payload = {
        "series": [
            {
                "idSerie": config.id,
                "idPeriodicidades": [config.periodicity_id],
            }
            for config in configs
        ],
        "fechaInicio": yyyymmdd(start_date),
        "fechaFin": yyyymmdd(end_date),
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Origin": "https://suameca.banrep.gov.co",
        "Referer": BANREP_REFERER,
    }

    try:
        with httpx.Client(
            timeout=timeout,
            follow_redirects=True,
            headers=headers,
            verify=_ssl_context(),
        ) as client:
            response = client.post(BANREP_URL, json=payload)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise MacroDataError(f"BanRep SUAMECA request failed: {exc}") from exc

    try:
        body = response.json()
    except ValueError as exc:
        preview = response.text[:500]
        raise MacroDataError(
            "BanRep SUAMECA did not return JSON. "
            f"First 500 characters: {preview!r}"
        ) from exc

    return normalize_banrep_response(
        body,
        start_date=start_date,
        end_date=end_date,
        series_keys=[config.key for config in configs],
    )
