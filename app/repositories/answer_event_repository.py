from uuid import UUID

import asyncpg


class AnswerEventRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def record(
        self,
        *,
        student_id: UUID,
        quest_id: UUID,
        question_id: UUID,
        student_quest_id: UUID,
        question_index: int,
        submitted_answer: str,
        is_correct: bool,
        served_difficulty: str | None = None,
        adaptation_action: str | None = None,
        adaptation_reason: str | None = None,
    ) -> None:
        await self.conn.execute(
            """INSERT INTO student_answer_events
               (student_id, quest_id, question_id, student_quest_id,
                question_index, submitted_answer, is_correct, served_difficulty,
                adaptation_action, adaptation_reason)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)""",
            student_id,
            quest_id,
            question_id,
            student_quest_id,
            question_index,
            submitted_answer,
            is_correct,
            served_difficulty,
            adaptation_action,
            adaptation_reason,
        )

    async def list_by_student_quest(self, student_quest_id: UUID) -> list[dict]:
        rows = await self.conn.fetch(
            """SELECT * FROM student_answer_events
               WHERE student_quest_id = $1
               ORDER BY question_index, answered_at, id""",
            student_quest_id,
        )
        return [dict(row) for row in rows]
