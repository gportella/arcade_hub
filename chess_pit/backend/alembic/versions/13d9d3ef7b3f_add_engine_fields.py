"""Add engine metadata fields to user table"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "13d9d3ef7b3f"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("is_engine", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "user",
        sa.Column("engine_key", sa.String(length=50), nullable=True),
    )
    op.create_unique_constraint("uq_user_engine_key", "user", ["engine_key"])
    op.alter_column("user", "is_engine", server_default=None)


def downgrade() -> None:
    op.drop_constraint("uq_user_engine_key", "user", type_="unique")
    op.drop_column("user", "engine_key")
    op.drop_column("user", "is_engine")
