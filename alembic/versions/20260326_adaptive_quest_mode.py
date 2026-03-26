"""adaptive quest mode

Revision ID: 20260326_adaptive_quest_mode
Revises: 20260326_iceberg
Create Date: 2026-03-26 00:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260326_adaptive_quest_mode"
down_revision: Union[str, Sequence[str], None] = "20260326_iceberg"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "quests",
        sa.Column(
            "delivery_mode",
            sa.Text(),
            nullable=False,
            server_default="fixed",
        ),
    )
    op.create_check_constraint(
        "quests_delivery_mode_check",
        "quests",
        "delivery_mode IN ('fixed','adaptive')",
    )


def downgrade() -> None:
    op.drop_constraint("quests_delivery_mode_check", "quests", type_="check")
    op.drop_column("quests", "delivery_mode")
