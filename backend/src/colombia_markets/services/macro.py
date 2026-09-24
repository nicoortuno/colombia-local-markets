"""Persist and query official macroeconomic observations."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from colombia_markets.analytics.macro import (
    basis_point_spread,
    usd_mn_to_bn,
    year_over_year_growth,
)
from colombia_markets.db.models.macro import MacroObservation
from colombia_markets.db.session import SessionLocal
from colombia_markets.ingestion.macro import SERIES
from colombia_markets.schemas.macro import (
    MacroDerivedMetric,
    MacroObservationPoint,
    MacroSeriesCatalogResponse,
    MacroSeriesHistoryResponse,
    MacroSeriesSummary,
    MacroSnapshotMetric,
    MacroSnapshotResponse,
)


SERIES_ORDER = [
    "policy_rate",
    "ibr_overnight",
    "headline_inflation",
    "core_inflation",
    "real_gdp",
    "unemployment",
    "current_account_gdp",
    "net_reserves",
]


def upsert_macro_observations(records: list[dict[str, Any]]) -> int:
    """Idempotent on (series_key, observation_date); atomic per ingestion run."""
    if not records:
        return 0

    with SessionLocal() as session:
        for offset in range(0, len(records), 500):
            chunk = records[offset : offset + 500]
            statement = insert(MacroObservation).values(chunk)
            statement = statement.on_conflict_do_update(
                constraint="uq_macro_observation_series_date",
                set_={
                    key: getattr(statement.excluded, key)
                    for key in (
                        "series_name",
                        "value",
                        "source_series_id",
                        "periodicity_id",
                        "frequency",
                        "unit",
                        "source",
                        "provider",
                    )
                }
                | {"ingested_at": func.now()},
            )
            session.execute(statement)
        session.commit()
    return len(records)


def get_latest_macro_dates() -> dict[str, date]:
    """Return the latest stored observation date for every populated series."""
    with SessionLocal() as session:
        rows = session.execute(
            select(
                MacroObservation.series_key,
                func.max(MacroObservation.observation_date),
            ).group_by(MacroObservation.series_key)
        ).all()
    return {series_key: latest_date for series_key, latest_date in rows}


def get_macro_row_counts() -> dict[str, int]:
    """Convenience diagnostic used by ingestion output and manual validation."""
    with SessionLocal() as session:
        rows = session.execute(
            select(
                MacroObservation.series_key,
                func.count(MacroObservation.id),
            ).group_by(MacroObservation.series_key)
        ).all()
    return {series_key: int(count) for series_key, count in rows}


def _float(value: Decimal) -> float:
    return float(value)


def _latest_rows(session, series_key: str, limit: int = 2) -> list[MacroObservation]:
    return list(
        session.scalars(
            select(MacroObservation)
            .where(MacroObservation.series_key == series_key)
            .order_by(MacroObservation.observation_date.desc())
            .limit(limit)
        ).all()
    )


def _summary_from_rows(rows: list[MacroObservation]) -> MacroSeriesSummary:
    if not rows:
        raise ValueError("No macro data is available for the requested series")

    latest = rows[0]
    previous = rows[1] if len(rows) > 1 else None
    latest_value = _float(latest.value)
    previous_value = _float(previous.value) if previous is not None else None

    change_abs: float | None = None
    change_pct: float | None = None
    if previous_value is not None:
        change_abs = round(latest_value - previous_value, 8)
        if previous_value != 0:
            change_pct = round((latest_value / previous_value - 1) * 100, 6)

    return MacroSeriesSummary(
        series_key=latest.series_key,
        series_name=latest.series_name,
        frequency=latest.frequency,
        unit=latest.unit,
        source=latest.source,
        provider=latest.provider,
        latest_date=latest.observation_date,
        latest_value=latest_value,
        previous_date=previous.observation_date if previous is not None else None,
        previous_value=previous_value,
        change_abs=change_abs,
        change_pct=change_pct,
    )


def get_macro_catalog() -> MacroSeriesCatalogResponse:
    """Return metadata and latest/previous observations for all stored macro series."""
    with SessionLocal() as session:
        summaries: list[MacroSeriesSummary] = []
        for key in SERIES_ORDER:
            rows = _latest_rows(session, key, limit=2)
            if rows:
                summaries.append(_summary_from_rows(rows))

    if not summaries:
        raise ValueError("No macro data is available")

    return MacroSeriesCatalogResponse(series=summaries)


def get_macro_series_history(
    series_key: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 5000,
) -> MacroSeriesHistoryResponse:
    """Return one stored macro series over an inclusive date range."""
    if series_key not in SERIES:
        raise ValueError(f"Unknown macro series key: {series_key}")
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
    if limit < 1 or limit > 10000:
        raise ValueError("limit must be between 1 and 10000")

    with SessionLocal() as session:
        latest = session.scalar(
            select(func.max(MacroObservation.observation_date)).where(
                MacroObservation.series_key == series_key
            )
        )
        if latest is None:
            raise ValueError(f"No macro data is available for {series_key}")

        resolved_end = min(end_date or latest, latest)
        resolved_start = start_date or (resolved_end - timedelta(days=5 * 365))
        if resolved_start > resolved_end:
            raise ValueError("No macro data in the requested interval")

        descending = session.scalars(
            select(MacroObservation)
            .where(
                MacroObservation.series_key == series_key,
                MacroObservation.observation_date >= resolved_start,
                MacroObservation.observation_date <= resolved_end,
            )
            .order_by(MacroObservation.observation_date.desc())
            .limit(limit)
        ).all()
        rows = list(reversed(descending))
        if not rows:
            raise ValueError("No macro data in the requested interval")

        first = rows[0]
        return MacroSeriesHistoryResponse(
            series_key=first.series_key,
            series_name=first.series_name,
            frequency=first.frequency,
            unit=first.unit,
            source=first.source,
            provider=first.provider,
            latest_date=latest,
            start_date=rows[0].observation_date,
            end_date=rows[-1].observation_date,
            points=[
                MacroObservationPoint(
                    observation_date=row.observation_date,
                    value=_float(row.value),
                )
                for row in rows
            ],
        )


def _snapshot_metric(row: MacroObservation) -> MacroSnapshotMetric:
    return MacroSnapshotMetric(
        value=_float(row.value),
        observation_date=row.observation_date,
        unit=row.unit,
        source=row.source,
    )


def _required_latest(session, series_key: str) -> MacroObservation:
    row = session.scalar(
        select(MacroObservation)
        .where(MacroObservation.series_key == series_key)
        .order_by(MacroObservation.observation_date.desc())
        .limit(1)
    )
    if row is None:
        raise ValueError(f"No macro data is available for {series_key}")
    return row


def get_macro_snapshot() -> MacroSnapshotResponse:
    """Return the latest market-facing macro snapshot plus derived metrics."""
    with SessionLocal() as session:
        policy = _required_latest(session, "policy_rate")
        ibr = _required_latest(session, "ibr_overnight")
        headline = _required_latest(session, "headline_inflation")
        core = _required_latest(session, "core_inflation")
        unemployment = _required_latest(session, "unemployment")
        gdp = _required_latest(session, "real_gdp")
        current_account = _required_latest(session, "current_account_gdp")
        reserves = _required_latest(session, "net_reserves")

        # Compare IBR with the policy rate prevailing on the IBR observation date,
        # rather than a potentially newer calendar-day policy observation.
        policy_for_ibr = session.scalar(
            select(MacroObservation)
            .where(
                MacroObservation.series_key == "policy_rate",
                MacroObservation.observation_date <= ibr.observation_date,
            )
            .order_by(MacroObservation.observation_date.desc())
            .limit(1)
        )
        if policy_for_ibr is None:
            raise ValueError("No policy-rate observation is available for the latest IBR date")

        prior_year_gdp_date = gdp.observation_date.replace(
            year=gdp.observation_date.year - 1
        )
        prior_year_gdp = session.scalar(
            select(MacroObservation).where(
                MacroObservation.series_key == "real_gdp",
                MacroObservation.observation_date == prior_year_gdp_date,
            )
        )
        if prior_year_gdp is None:
            raise ValueError(
                "Cannot calculate GDP YoY: prior-year quarter is missing "
                f"({prior_year_gdp_date})"
            )

        spread_bp = basis_point_spread(
            _float(ibr.value),
            _float(policy_for_ibr.value),
        )
        gdp_yoy = year_over_year_growth(
            _float(gdp.value),
            _float(prior_year_gdp.value),
        )
        reserves_bn = usd_mn_to_bn(_float(reserves.value))

        latest_dates = [
            policy.observation_date,
            ibr.observation_date,
            headline.observation_date,
            core.observation_date,
            unemployment.observation_date,
            gdp.observation_date,
            current_account.observation_date,
            reserves.observation_date,
        ]

        return MacroSnapshotResponse(
            as_of_date=max(latest_dates),
            policy_rate=_snapshot_metric(policy),
            ibr_overnight=_snapshot_metric(ibr),
            ibr_policy_spread_bp=MacroDerivedMetric(
                value=spread_bp,
                observation_date=ibr.observation_date,
                unit="bp",
                comparison_date=policy_for_ibr.observation_date,
            ),
            headline_inflation=_snapshot_metric(headline),
            core_inflation=_snapshot_metric(core),
            unemployment=_snapshot_metric(unemployment),
            real_gdp_yoy=MacroDerivedMetric(
                value=gdp_yoy,
                observation_date=gdp.observation_date,
                unit="% YoY",
                comparison_date=prior_year_gdp.observation_date,
            ),
            current_account_gdp=_snapshot_metric(current_account),
            net_reserves=_snapshot_metric(reserves),
            net_reserves_usd_bn=MacroDerivedMetric(
                value=reserves_bn,
                observation_date=reserves.observation_date,
                unit="USD bn",
            ),
        )
