"""Exercise the standalone new migration against an in-memory DB."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects.postgresql import insert

from colombia_markets.db.models.fx import FxDailyMarket


def test_fx_migration_up_and_down():
    path = Path(__file__).resolve().parents[1] / "migrations/versions/c8327a9f5e11_add_fx_daily_market.py"
    spec = spec_from_file_location("fx_migration_under_test", path)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    assert migration.down_revision == "7960d971120e"

    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.begin() as connection:
        migration_context = MigrationContext.configure(connection)
        with Operations.context(migration_context):
            migration.upgrade()
        inspector = inspect(connection)
        assert "fx_daily_market" in inspector.get_table_names()
        indexes = inspector.get_indexes("fx_daily_market")
        assert any(index["name"] == "ix_fx_daily_market_pair_source_date" for index in indexes)
        unique = inspector.get_unique_constraints("fx_daily_market")
        assert any(c["name"] == "uq_fx_daily_market_date_pair_source" for c in unique)
        with Operations.context(migration_context):
            migration.downgrade()
        assert "fx_daily_market" not in inspect(connection).get_table_names()
    engine.dispose()


def test_postgres_upsert_statement_compiles():
    stmt = insert(FxDailyMarket).values(
        trade_date="2026-07-01", pair="USD/COP", source="yahoo_finance",
        open_price=3429, high_price=3439, low_price=3403, close_price=3429,
    )
    upsert = stmt.on_conflict_do_update(
        constraint="uq_fx_daily_market_date_pair_source",
        set_={"close_price": stmt.excluded.close_price},
    )
    assert "ON CONFLICT ON CONSTRAINT uq_fx_daily_market_date_pair_source" in str(upsert.compile())
