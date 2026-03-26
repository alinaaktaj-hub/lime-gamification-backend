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
    ) -> None:
        await self.conn.execute(
            """INSERT INTO student_answer_events
               (student_id, quest_id, question_id, student_quest_id,
                question_index, submitted_answer, is_correct)
               VALUES ($1, $2, $3, $4, $5, $6, $7)""",
            student_id,
            quest_id,
            question_id,
            student_quest_id,
            question_index,
            submitted_answer,
            is_correct,
        )
