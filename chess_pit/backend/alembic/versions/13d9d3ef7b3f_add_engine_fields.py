"""Add engine metadata fields to user table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "13d9d3ef7b3f"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("user")}

    if "is_engine" not in existing_columns:
        op.add_column(
            "user",
            sa.Column("is_engine", sa.Boolean(), nullable=False, server_default="0"),
        )
    if "engine_key" not in existing_columns:
        op.add_column(
            "user",
            sa.Column("engine_key", sa.String(length=50), nullable=True),
        )

    existing_indexes = {index["name"] for index in inspector.get_indexes("user")}
    if "uq_user_engine_key" not in existing_indexes:
        op.create_index(
            "uq_user_engine_key",
            "user",
            ["engine_key"],
            unique=True,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_indexes = {index["name"] for index in inspector.get_indexes("user")}
    if "uq_user_engine_key" in existing_indexes:
        op.drop_index("uq_user_engine_key", table_name="user")

    existing_columns = {column["name"] for column in inspector.get_columns("user")}
    if "engine_key" in existing_columns:
        op.drop_column("user", "engine_key")
    if "is_engine" in existing_columns:
        op.drop_column("user", "is_engine")
