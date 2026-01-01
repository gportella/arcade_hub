"""Add rating column to user table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "9b36a6c6a3a8"
down_revision = "6b7f4e1f4f9a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user")}
    if "rating" not in columns:
        op.add_column(
            "user",
            sa.Column("rating", sa.Integer(), nullable=False, server_default="1200"),
        )
        op.execute(sa.text('UPDATE "user" SET rating = 1200 WHERE rating IS NULL'))
        op.alter_column("user", "rating", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("user")}
    if "rating" in columns:
        op.drop_column("user", "rating")
