from datetime import date
from decimal import Decimal
import importlib
import sys
import types

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from colombia_markets.db.base import Base
from colombia_markets.db.models.fx import FxDailyMarket


@pytest.fixture
def service(monkeypatch):
    """Exercise SQL read paths against SQLite, without external Postgres."""
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    stub = types.ModuleType("colombia_markets.db.session")
    stub.SessionLocal = factory
    monkeypatch.setitem(sys.modules, "colombia_markets.db.session", stub)
    sys.modules.pop("colombia_markets.services.fx", None)
    mod = importlib.import_module("colombia_markets.services.fx")
    yield mod, factory
    sys.modules.pop("colombia_markets.services.fx", None)
    engine.dispose()


def seed(factory):
    with factory.begin() as session:
        for day, close in [(1, "3400"), (2, "3434"), (3, "3468.34")]:
            session.add(
                FxDailyMarket(
                    trade_date=date(2026, 7, day),
                    pair="USD/COP", source="yahoo_finance",
                    open_price=Decimal(close), high_price=Decimal(close),
                    low_price=Decimal(close), close_price=Decimal(close),
                )
            )


def test_history_returns_changes_and_full_latest_date(service):
    mod, factory = service
    seed(factory)
    response = mod.get_usdcop_history(date(2026, 7, 2), date(2026, 7, 3))
    assert response.latest_date == date(2026, 7, 3)
    assert len(response.points) == 2
    assert response.points[0].change_1d_pct == 1.0
    assert response.points[1].change_1d_cop == 34.34
    assert mod.get_latest_fx_date() == date(2026, 7, 3)


def test_latest_uses_previous_stored_quote(service):
    mod, factory = service
    seed(factory)
    response = mod.get_latest_usdcop()
    assert response.point.trade_date == date(2026, 7, 3)
    assert response.point.change_1d_pct == 1.0


def test_unique_date_pair_source_constraint(service):
    from sqlalchemy.exc import IntegrityError
    mod, factory = service
    seed(factory)
    with pytest.raises(IntegrityError):
        with factory.begin() as session:
            session.add(
                FxDailyMarket(
                    trade_date=date(2026, 7, 1), pair="USD/COP", source="yahoo_finance",
                    open_price=Decimal(1), high_price=Decimal(1),
                    low_price=Decimal(1), close_price=Decimal(1),
                )
            )
            session.flush()
