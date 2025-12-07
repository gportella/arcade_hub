"""Add PGN and initial FEN columns to game."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20241207_0002"
down_revision: Union[str, None] = "20241207_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULT_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def upgrade() -> None:
    op.add_column(
        "game",
        sa.Column(
            "initial_fen",
            sa.String(length=100),
            nullable=False,
            server_default=_DEFAULT_FEN,
        ),
    )
    op.add_column(
        "game",
        sa.Column(
            "pgn",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.alter_column("game", "initial_fen", server_default=None)
    op.alter_column("game", "pgn", server_default=None)


def downgrade() -> None:
    op.drop_column("game", "pgn")
    op.drop_column("game", "initial_fen")
