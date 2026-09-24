"""Add vendor-labelled daily FX OHLC observations.

Revision ID: c8327a9f5e11
Revises: 7960d971120e
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "c8327a9f5e11"
down_revision: str | None = "7960d971120e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fx_daily_market",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("pair", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("open_price", sa.Numeric(precision=16, scale=6), nullable=False),
        sa.Column("high_price", sa.Numeric(precision=16, scale=6), nullable=False),
        sa.Column("low_price", sa.Numeric(precision=16, scale=6), nullable=False),
        sa.Column("close_price", sa.Numeric(precision=16, scale=6), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "trade_date", "pair", "source", name="uq_fx_daily_market_date_pair_source"
        ),
    )
    op.create_index(
        "ix_fx_daily_market_pair_source_date",
        "fx_daily_market",
        ["pair", "source", "trade_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_fx_daily_market_pair_source_date", table_name="fx_daily_market")
    op.drop_table("fx_daily_market")
