# USD/COP daily FX ingestion (Yahoo)

This adds **vendor-labelled**, daily USD/COP OHLC (`COP=X`) to PostgreSQL.
Yahoo's daily session dates and OHLC conventions are **not** the official
Colombian SET-FX close or the certified TRM. Do not silently combine them.

## Installation

From the repository root, extract the update zip. From `backend/`:

```bash
uv sync
# Confirm that `uv run alembic heads` shows the new FX revision.
uv run alembic upgrade head
```

If `alembic heads` reports more than one head or an unknown parent revision,
check the existing TES revision ID before upgrading. This FX migration expects
TES revision `7960d971120e` as its parent. The migration *adds* an FX table;
it does not modify TES data.

The script bootstraps the repository's `backend/src` path, so no manual
`PYTHONPATH` should be necessary for this command.

```bash
# Initial inclusive backfill
uv run python ../scripts/ingest_fx.py --start 2026-07-01 --end 2026-09-21

# Later, automatically resume with five calendar days' overlap
uv run python ../scripts/ingest_fx.py --update

# Optionally, after market hours, include today's possibly revisable data
uv run python ../scripts/ingest_fx.py --update --include-today
```

By default, the maximum end date is **yesterday in America/Bogota**. This
avoids recording a partial same-day Yahoo bar as a completed trading day.
`--include-today` overrides that safety rule. Each run upserts, rechecking
the latest five calendar days; re-running does not create duplicate rows.
Yahoo's `end` argument is exclusive, so the script adds one day to user-supplied
inclusive `--end` when requesting history.

The service commits rows in batches of at most 500 within one transaction.
The unique constraint is `(trade_date, pair, source)`.

## API

With Uvicorn running:

- `GET /fx/usdcop/latest`
- `GET /fx/usdcop/history?start_date=2026-07-01&end_date=2026-09-21`

The history API defaults to the past year and returns at most the latest 2,000
observations (up to 5,000 via `limit`). `change_1d_cop` and `change_1d_pct`
are based on the immediately preceding stored Yahoo session, including when
the requested date window begins after the start of available history.
No FX frontend changes are included in this release.

## Database checks

```bash
docker exec colombia-markets-postgres psql -U colombia -d colombia_markets \
  -c "SELECT MIN(trade_date), MAX(trade_date), COUNT(*) FROM fx_daily_market;"

docker exec colombia-markets-postgres psql -U colombia -d colombia_markets \
  -c "SELECT trade_date, pair, source, COUNT(*) FROM fx_daily_market
       GROUP BY trade_date,pair,source HAVING COUNT(*) > 1;"
```

A future enhancement will ingest Colombia's official TRM into a *separate*
reference-rate series with effective-date semantics. It should not overwrite
or be conflated with Yahoo spot quotes.
