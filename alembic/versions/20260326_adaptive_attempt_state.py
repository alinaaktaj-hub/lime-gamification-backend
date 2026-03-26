"""adaptive attempt state

Revision ID: 20260326_adaptive_attempt_state
Revises: 20260326_adaptive_question_metadata
Create Date: 2026-03-26 00:30:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260326_adaptive_attempt_state"
down_revision: Union[str, Sequence[str], None] = "20260326_adaptive_question_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "student_quests",
        sa.Column("current_question_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "student_quests",
        sa.Column("current_difficulty_level", sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        "student_quests_current_question_id_fkey",
        "student_quests",
        "questions",
        ["current_question_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "student_quests_current_difficulty_level_check",
        "student_quests",
        "current_difficulty_level IS NULL OR current_difficulty_level IN ('easy','medium','hard')",
    )

    op.add_column(
        "student_answer_events",
        sa.Column("served_difficulty", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_answer_events",
        sa.Column("adaptation_action", sa.Text(), nullable=True),
    )
    op.add_column(
        "student_answer_events",
        sa.Column("adaptation_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("student_answer_events", "adaptation_reason")
    op.drop_column("student_answer_events", "adaptation_action")
    op.drop_column("student_answer_events", "served_difficulty")
    op.drop_constraint(
        "student_quests_current_difficulty_level_check",
        "student_quests",
        type_="check",
    )
    op.drop_constraint(
        "student_quests_current_question_id_fkey",
        "student_quests",
        type_="foreignkey",
    )
    op.drop_column("student_quests", "current_difficulty_level")
    op.drop_column("student_quests", "current_question_id")
