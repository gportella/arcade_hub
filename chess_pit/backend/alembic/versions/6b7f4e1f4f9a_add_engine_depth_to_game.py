"""Add engine depth to game table"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "6b7f4e1f4f9a"
down_revision = "13d9d3ef7b3f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("game")}

    if "engine_depth" not in existing_columns:
        op.add_column(
            "game",
            sa.Column("engine_depth", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("game")}

    if "engine_depth" in existing_columns:
        op.drop_column("game", "engine_depth")
