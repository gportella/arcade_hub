"""Add puzzle and attempt tables"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260102_add_puzzles_tables"
down_revision = "20260101_add_time_controls"
branch_labels = None
depends_on = None


PUZZLE_TABLE = "puzzle"
PUZZLE_ATTEMPT_TABLE = "puzzleattempt"
PUZZLE_DIFFICULTY_ENUM = sa.Enum(
    "easy",
    "medium",
    "hard",
    "expert",
    name="puzzledifficulty",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if bind.dialect.name != "sqlite":
        PUZZLE_DIFFICULTY_ENUM.create(bind, checkfirst=True)

    puzzle_exists = inspector.has_table(PUZZLE_TABLE)
    if not puzzle_exists:
        op.create_table(
            PUZZLE_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cool_id", sa.String(length=40), nullable=False, unique=True),
            sa.Column("fen", sa.String(length=100), nullable=False),
            sa.Column("difficulty", PUZZLE_DIFFICULTY_ENUM, nullable=False, index=True),
            sa.Column("source", sa.String(length=100), nullable=True),
            sa.Column("hint", sa.String(length=255), nullable=True),
            sa.Column("solution_moves", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("presented_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("solve_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("fail_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("hint_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )

    existing_puzzle_indexes = {index["name"] for index in inspector.get_indexes(PUZZLE_TABLE)}
    if "ix_puzzle_cool_id" not in existing_puzzle_indexes:
        op.create_index(
            "ix_puzzle_cool_id",
            PUZZLE_TABLE,
            ["cool_id"],
            unique=True,
        )
    if "ix_puzzle_difficulty" not in existing_puzzle_indexes:
        op.create_index(
            "ix_puzzle_difficulty",
            PUZZLE_TABLE,
            ["difficulty"],
        )

    attempt_exists = inspector.has_table(PUZZLE_ATTEMPT_TABLE)
    if not attempt_exists:
        op.create_table(
            PUZZLE_ATTEMPT_TABLE,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "puzzle_id",
                sa.Integer(),
                sa.ForeignKey(f"{PUZZLE_TABLE}.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("user.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column(
                "solved",
                sa.Boolean(),
                nullable=False,
                server_default=sa.sql.expression.false(),
            ),
            sa.Column("hint_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("points_awarded", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("submitted_moves", sa.JSON(), nullable=False, server_default="[]"),
        )

    if attempt_exists:
        existing_attempt_indexes = {
            index["name"] for index in inspector.get_indexes(PUZZLE_ATTEMPT_TABLE)
        }
    else:
        existing_attempt_indexes = set()

    if "ix_puzzleattempt_puzzle_user" not in existing_attempt_indexes:
        op.create_index(
            "ix_puzzleattempt_puzzle_user",
            PUZZLE_ATTEMPT_TABLE,
            ["puzzle_id", "user_id"],
        )
    if "ix_puzzleattempt_user_id" not in existing_attempt_indexes:
        op.create_index(
            "ix_puzzleattempt_user_id",
            PUZZLE_ATTEMPT_TABLE,
            ["user_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table(PUZZLE_ATTEMPT_TABLE):
        existing_attempt_indexes = {
            index["name"] for index in inspector.get_indexes(PUZZLE_ATTEMPT_TABLE)
        }
        if "ix_puzzleattempt_user_id" in existing_attempt_indexes:
            op.drop_index("ix_puzzleattempt_user_id", table_name=PUZZLE_ATTEMPT_TABLE)
        if "ix_puzzleattempt_puzzle_user" in existing_attempt_indexes:
            op.drop_index("ix_puzzleattempt_puzzle_user", table_name=PUZZLE_ATTEMPT_TABLE)
        op.drop_table(PUZZLE_ATTEMPT_TABLE)

    if inspector.has_table(PUZZLE_TABLE):
        existing_puzzle_indexes = {index["name"] for index in inspector.get_indexes(PUZZLE_TABLE)}
        if "ix_puzzle_difficulty" in existing_puzzle_indexes:
            op.drop_index("ix_puzzle_difficulty", table_name=PUZZLE_TABLE)
        if "ix_puzzle_cool_id" in existing_puzzle_indexes:
            op.drop_index("ix_puzzle_cool_id", table_name=PUZZLE_TABLE)
        op.drop_table(PUZZLE_TABLE)

    if bind.dialect.name != "sqlite":
        PUZZLE_DIFFICULTY_ENUM.drop(bind, checkfirst=True)
