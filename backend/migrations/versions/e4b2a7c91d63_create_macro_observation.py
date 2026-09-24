"""Create unified macro observation table.

Revision ID: e4b2a7c91d63
Revises: c8327a9f5e11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "e4b2a7c91d63"
down_revision: str | None = "c8327a9f5e11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "macro_observation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("series_key", sa.String(length=40), nullable=False),
        sa.Column("series_name", sa.String(length=180), nullable=False),
        sa.Column("observation_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("source_series_id", sa.Integer(), nullable=False),
        sa.Column("periodicity_id", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.String(length=32), nullable=False),
        sa.Column("unit", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=160), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "series_key",
            "observation_date",
            name="uq_macro_observation_series_date",
        ),
    )
    op.create_index(
        "ix_macro_observation_series_date",
        "macro_observation",
        ["series_key", "observation_date"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_macro_observation_series_date",
        table_name="macro_observation",
    )
    op.drop_table("macro_observation")
