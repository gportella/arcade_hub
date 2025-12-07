"""Initial Chess Pit schema."""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20241207_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("avatar_url", sa.String(length=255), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("games_played", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_won", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_lost", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("games_drawn", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_user_username", "user", ["username"], unique=True)

    gamestatus = sa.Enum("pending", "active", "completed", "aborted", name="gamestatus")
    gameresult = sa.Enum("white", "black", "draw", name="gameresult")

    op.create_table(
        "game",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("white_player_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("black_player_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("status", gamestatus, nullable=False, server_default="pending"),
        sa.Column("result", gameresult, nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("last_move_at", sa.DateTime(), nullable=True),
        sa.Column("moves_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_game_status", "game", ["status"])
    op.create_index("ix_game_started_at", "game", ["started_at"])
    op.create_index("ix_game_last_move_at", "game", ["last_move_at"])

    op.create_table(
        "move",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("game.id"), nullable=False),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("move_number", sa.Integer(), nullable=False),
        sa.Column("notation", sa.String(length=12), nullable=False),
        sa.Column("played_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("game_id", "move_number"),
    )
    op.create_index("ix_move_game_id", "move", ["game_id"])
    op.create_index("ix_move_played_at", "move", ["played_at"])


def downgrade() -> None:
    op.drop_index("ix_move_played_at", table_name="move")
    op.drop_index("ix_move_game_id", table_name="move")
    op.drop_table("move")

    op.drop_index("ix_game_last_move_at", table_name="game")
    op.drop_index("ix_game_started_at", table_name="game")
    op.drop_index("ix_game_status", table_name="game")
    op.drop_table("game")

    op.drop_index("ix_user_username", table_name="user")
    op.drop_table("user")

    gameresult = sa.Enum("white", "black", "draw", name="gameresult")
    gamestatus = sa.Enum("pending", "active", "completed", "aborted", name="gamestatus")
    gameresult.drop(op.get_bind(), checkfirst=True)
    gamestatus.drop(op.get_bind(), checkfirst=True)
