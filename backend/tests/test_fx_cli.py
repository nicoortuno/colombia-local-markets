from datetime import date
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
import types

import pytest


def load_cli(monkeypatch):
    """Stub the DB service so window logic is tested without Postgres."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    dummy = types.ModuleType("colombia_markets.services.fx")
    dummy.get_latest_fx_date = lambda: None
    dummy.upsert_fx_daily_market = lambda records: len(records)
    monkeypatch.setitem(sys.modules, "colombia_markets.services.fx", dummy)
    path = Path(__file__).resolve().parents[2] / "scripts" / "ingest_fx.py"
    spec = spec_from_file_location("fx_cli_test", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_update_overlaps_last_ingested_date(monkeypatch):
    cli = load_cli(monkeypatch)
    start, end = cli.determine_window(
        update=True, start_date=None, end_date=None,
        last_stored_date=date(2026, 9, 21), today_bogota=date(2026, 9, 23)
    )
    assert start == date(2026, 9, 16)
    assert end == date(2026, 9, 22)


def test_initial_update_starts_july_first(monkeypatch):
    cli = load_cli(monkeypatch)
    start, end = cli.determine_window(
        update=True, start_date=None, end_date=None,
        last_stored_date=None, today_bogota=date(2026, 9, 22)
    )
    assert (start, end) == (date(2026, 7, 1), date(2026, 9, 21))


def test_same_day_requires_opt_in(monkeypatch):
    cli = load_cli(monkeypatch)
    with pytest.raises(ValueError, match="include-today"):
        cli.determine_window(
            update=False, start_date=date(2026, 9, 21), end_date=date(2026, 9, 22),
            last_stored_date=None, today_bogota=date(2026, 9, 22)
        )
