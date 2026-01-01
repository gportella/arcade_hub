"""Add time control fields to game table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260101_add_time_controls"
down_revision = "9b36a6c6a3a8"
branch_labels = None
depends_on = None


GAME_TABLE = "game"


def _column_names(bind) -> set[str]:
    inspector = sa.inspect(bind)
    return {column["name"] for column in inspector.get_columns(GAME_TABLE)}


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns = _column_names(bind)

    if "time_control_initial_seconds" not in existing_columns:
        op.add_column(
            GAME_TABLE,
            sa.Column("time_control_initial_seconds", sa.Integer(), nullable=True),
        )
    if "time_control_increment_seconds" not in existing_columns:
        op.add_column(
            GAME_TABLE,
            sa.Column("time_control_increment_seconds", sa.Integer(), nullable=True),
        )
    if "white_time_remaining_seconds" not in existing_columns:
        op.add_column(
            GAME_TABLE,
            sa.Column("white_time_remaining_seconds", sa.Integer(), nullable=True),
        )
    if "black_time_remaining_seconds" not in existing_columns:
        op.add_column(
            GAME_TABLE,
            sa.Column("black_time_remaining_seconds", sa.Integer(), nullable=True),
        )
    if "turn_start_time" not in existing_columns:
        op.add_column(
            GAME_TABLE,
            sa.Column("turn_start_time", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing_columns = _column_names(bind)

    if "turn_start_time" in existing_columns:
        op.drop_column(GAME_TABLE, "turn_start_time")
    if "black_time_remaining_seconds" in existing_columns:
        op.drop_column(GAME_TABLE, "black_time_remaining_seconds")
    if "white_time_remaining_seconds" in existing_columns:
        op.drop_column(GAME_TABLE, "white_time_remaining_seconds")
    if "time_control_increment_seconds" in existing_columns:
        op.drop_column(GAME_TABLE, "time_control_increment_seconds")
    if "time_control_initial_seconds" in existing_columns:
        op.drop_column(GAME_TABLE, "time_control_initial_seconds")
