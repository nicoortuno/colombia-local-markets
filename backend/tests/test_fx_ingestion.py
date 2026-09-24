from datetime import date
from decimal import Decimal
import sys
import types

import pandas as pd
import pytest

from colombia_markets.ingestion.fx import (
    FxDataError,
    download_yahoo_usdcop,
    normalize_yahoo_history,
)


def example_history():
    return pd.DataFrame(
        {
            "Open": [3429.459961, 3387.23999],
            "High": [3439.35, 3387.33],
            "Low": [3403.12, 3351.53],
            "Close": [3429.459961, 3387.23999],
        },
        index=pd.DatetimeIndex(
            ["2026-07-01 00:00:00+01:00", "2026-07-02 00:00:00+01:00"]
        ),
    )


def test_vendor_session_dates_preserved_with_timezone_offset():
    records = normalize_yahoo_history(example_history(), date(2026, 7, 1), date(2026, 7, 2))
    assert [r["trade_date"] for r in records] == [date(2026, 7, 1), date(2026, 7, 2)]
    assert records[0]["close_price"] == Decimal("3429.459961")
    assert records[0]["pair"] == "USD/COP"
    assert records[0]["source"] == "yahoo_finance"


def test_requested_range_is_inclusive_and_filters_vendor_extra_dates():
    records = normalize_yahoo_history(example_history(), date(2026, 7, 2), date(2026, 7, 2))
    assert len(records) == 1
    assert records[0]["trade_date"] == date(2026, 7, 2)


def test_rejects_nonpositive_prices():
    history = example_history()
    history.loc[history.index[0], "Close"] = 0
    with pytest.raises(FxDataError, match="invalid close"):
        normalize_yahoo_history(history, date(2026, 7, 1), date(2026, 7, 2))


def test_rejects_inverted_high_low():
    history = example_history()
    history.loc[history.index[0], "High"] = 3000
    with pytest.raises(FxDataError, match="high is below low"):
        normalize_yahoo_history(history, date(2026, 7, 1), date(2026, 7, 2))


def test_conflicting_duplicate_session_detected():
    history = pd.concat([example_history().iloc[:1], example_history().iloc[:1]])
    history.iloc[-1, history.columns.get_loc("Close")] = 3200
    with pytest.raises(FxDataError, match="Conflicting"):
        normalize_yahoo_history(history, date(2026, 7, 1), date(2026, 7, 2))


def test_download_uses_exclusive_yahoo_end(monkeypatch):
    calls = {}

    class FakeTicker:
        def __init__(self, ticker):
            assert ticker == "COP=X"

        def history(self, **kwargs):
            calls.update(kwargs)
            return example_history()

    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Ticker=FakeTicker))
    records = download_yahoo_usdcop(date(2026, 7, 1), date(2026, 7, 2))
    assert len(records) == 2
    assert calls["start"] == "2026-07-01"
    assert calls["end"] == "2026-07-03"
    assert calls["interval"] == "1d"


def test_weeklong_empty_download_is_an_error(monkeypatch):
    class FakeTicker:
        def __init__(self, ticker):
            pass

        def history(self, **kwargs):
            return pd.DataFrame()

    monkeypatch.setitem(sys.modules, "yfinance", types.SimpleNamespace(Ticker=FakeTicker))
    with pytest.raises(FxDataError, match="no observations"):
        download_yahoo_usdcop(date(2026, 7, 6), date(2026, 7, 10))
