"""adaptive question metadata

Revision ID: 20260326_adaptive_question_metadata
Revises: 20260326_adaptive_quest_mode
Create Date: 2026-03-26 00:20:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260326_adaptive_question_metadata"
down_revision: Union[str, Sequence[str], None] = "20260326_adaptive_quest_mode"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("difficulty_level", sa.Text(), nullable=True))
    op.add_column(
        "questions",
        sa.Column("difficulty_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("difficulty_rationale", sa.Text(), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("difficulty_scored_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("difficulty_model_version", sa.Text(), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column("difficulty_confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "questions",
        sa.Column(
            "difficulty_needs_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.create_check_constraint(
        "questions_difficulty_level_check",
        "questions",
        "difficulty_level IS NULL OR difficulty_level IN ('easy','medium','hard')",
    )
    op.create_check_constraint(
        "questions_difficulty_score_check",
        "questions",
        "difficulty_score IS NULL OR (difficulty_score >= 0 AND difficulty_score <= 1)",
    )
    op.create_check_constraint(
        "questions_difficulty_confidence_check",
        "questions",
        "difficulty_confidence IS NULL OR (difficulty_confidence >= 0 AND difficulty_confidence <= 1)",
    )


def downgrade() -> None:
    op.drop_constraint("questions_difficulty_confidence_check", "questions", type_="check")
    op.drop_constraint("questions_difficulty_score_check", "questions", type_="check")
    op.drop_constraint("questions_difficulty_level_check", "questions", type_="check")
    op.drop_column("questions", "difficulty_needs_review")
    op.drop_column("questions", "difficulty_confidence")
    op.drop_column("questions", "difficulty_model_version")
    op.drop_column("questions", "difficulty_scored_at")
    op.drop_column("questions", "difficulty_rationale")
    op.drop_column("questions", "difficulty_score")
    op.drop_column("questions", "difficulty_level")
