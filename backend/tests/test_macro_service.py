from datetime import date
from decimal import Decimal
import importlib
import sys
import types

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from colombia_markets.db.base import Base
from colombia_markets.db.models.macro import MacroObservation


@pytest.fixture
def service(monkeypatch):
    """Exercise macro read paths against SQLite without external Postgres."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    stub = types.ModuleType("colombia_markets.db.session")
    stub.SessionLocal = factory
    monkeypatch.setitem(sys.modules, "colombia_markets.db.session", stub)
    sys.modules.pop("colombia_markets.services.macro", None)
    mod = importlib.import_module("colombia_markets.services.macro")
    yield mod, factory
    sys.modules.pop("colombia_markets.services.macro", None)
    engine.dispose()


def add_row(factory, key, name, observed, value, frequency, unit, source="Banco de la República"):
    config_ids = {
        "policy_rate": (59, 1),
        "ibr_overnight": (15324, 1),
        "headline_inflation": (15270, 9),
        "core_inflation": (15390, 9),
        "real_gdp": (15154, 12),
        "unemployment": (15312, 9),
        "current_account_gdp": (15290, 12),
        "net_reserves": (15051, 9),
    }
    source_id, periodicity_id = config_ids[key]
    with factory.begin() as session:
        session.add(
            MacroObservation(
                series_key=key,
                series_name=name,
                observation_date=observed,
                value=Decimal(str(value)),
                source_series_id=source_id,
                periodicity_id=periodicity_id,
                frequency=frequency,
                unit=unit,
                source=source,
                provider="banrep_suameca",
            )
        )


def seed_snapshot(factory):
    add_row(factory, "policy_rate", "Tasa de política monetaria", date(2026, 9, 22), 12, "daily_calendar", "%")
    add_row(factory, "policy_rate", "Tasa de política monetaria", date(2026, 9, 23), 12, "daily_calendar", "%")
    add_row(factory, "ibr_overnight", "IBR", date(2026, 9, 23), 12.002, "daily_business", "%")
    add_row(factory, "headline_inflation", "Headline", date(2026, 8, 31), 6.24, "monthly", "%", "DANE")
    add_row(factory, "core_inflation", "Core", date(2026, 8, 31), 6.12, "monthly", "%")
    add_row(factory, "unemployment", "Unemployment", date(2026, 7, 31), 8.1, "monthly", "%", "DANE")
    add_row(factory, "real_gdp", "GDP", date(2025, 6, 30), 248150.38, "quarterly", "COP bn", "DANE")
    add_row(factory, "real_gdp", "GDP", date(2026, 6, 30), 256893.70, "quarterly", "COP bn", "DANE")
    add_row(factory, "current_account_gdp", "CA", date(2026, 6, 30), -3.5, "quarterly", "% GDP")
    add_row(factory, "net_reserves", "Reserves", date(2026, 8, 31), 67816.9, "monthly", "USD mn")


def test_snapshot_calculates_market_metrics(service):
    mod, factory = service
    seed_snapshot(factory)

    result = mod.get_macro_snapshot()

    assert result.as_of_date == date(2026, 9, 23)
    assert result.policy_rate.value == 12.0
    assert result.ibr_policy_spread_bp.value == 0.2
    assert result.real_gdp_yoy.value == pytest.approx(3.5234, rel=1e-4)
    assert result.net_reserves_usd_bn.value == pytest.approx(67.8169)


def test_history_is_chronological_and_date_filtered(service):
    mod, factory = service
    for month, value in [(1, 5.0), (2, 5.2), (3, 5.4)]:
        add_row(
            factory,
            "headline_inflation",
            "Inflación total anual",
            date(2026, month, 28 if month == 2 else 31),
            value,
            "monthly",
            "%",
            "DANE",
        )

    result = mod.get_macro_series_history(
        "headline_inflation",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 3, 31),
    )

    assert [point.value for point in result.points] == [5.2, 5.4]
    assert result.latest_date == date(2026, 3, 31)
    assert result.start_date == date(2026, 2, 28)
    assert result.end_date == date(2026, 3, 31)


def test_catalog_returns_latest_and_previous_change(service):
    mod, factory = service
    add_row(factory, "policy_rate", "Tasa de política monetaria", date(2026, 9, 22), 11.75, "daily_calendar", "%")
    add_row(factory, "policy_rate", "Tasa de política monetaria", date(2026, 9, 23), 12.0, "daily_calendar", "%")

    catalog = mod.get_macro_catalog()
    policy = catalog.series[0]

    assert policy.series_key == "policy_rate"
    assert policy.latest_value == 12.0
    assert policy.previous_value == 11.75
    assert policy.change_abs == 0.25


def test_unknown_series_rejected(service):
    mod, _ = service
    with pytest.raises(ValueError, match="Unknown macro series key"):
        mod.get_macro_series_history("not_a_series")
