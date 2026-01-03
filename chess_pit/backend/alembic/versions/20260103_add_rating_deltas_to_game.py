"""Add rating delta columns to game table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260103_add_rating_deltas_to_game"
down_revision = "20260102_add_puzzles_tables"
branch_labels = None
depends_on = None

GAME_TABLE = "game"


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns(GAME_TABLE)}

    if "white_rating_delta" not in existing_columns:
        op.add_column(
            GAME_TABLE,
            sa.Column("white_rating_delta", sa.Integer(), nullable=False, server_default="0"),
        )
    if "black_rating_delta" not in existing_columns:
        op.add_column(
            GAME_TABLE,
            sa.Column("black_rating_delta", sa.Integer(), nullable=False, server_default="0"),
        )

    if bind.dialect.name != "sqlite":
        op.execute(sa.text("UPDATE game SET white_rating_delta = 0 WHERE white_rating_delta IS NULL"))
        op.execute(sa.text("UPDATE game SET black_rating_delta = 0 WHERE black_rating_delta IS NULL"))
    else:
        op.execute("UPDATE game SET white_rating_delta = 0 WHERE white_rating_delta IS NULL")
        op.execute("UPDATE game SET black_rating_delta = 0 WHERE black_rating_delta IS NULL")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns(GAME_TABLE)}

    if "white_rating_delta" in existing_columns:
        op.drop_column(GAME_TABLE, "white_rating_delta")
    if "black_rating_delta" in existing_columns:
        op.drop_column(GAME_TABLE, "black_rating_delta")
