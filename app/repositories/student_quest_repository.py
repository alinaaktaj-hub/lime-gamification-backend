from typing import Optional, List
from uuid import UUID

import asyncpg

from app.entities.student_quest import StudentQuestEntity


class StudentQuestRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def find_active(
        self, student_id: UUID, quest_id: UUID
    ) -> Optional[StudentQuestEntity]:
        row = await self.conn.fetchrow(
            """SELECT * FROM student_quests
               WHERE student_id = $1 AND quest_id = $2 AND status = 'in_progress'""",
            student_id, quest_id,
        )
        return StudentQuestEntity(**dict(row)) if row else None

    async def find_any(
        self, student_id: UUID, quest_id: UUID
    ) -> Optional[StudentQuestEntity]:
        row = await self.conn.fetchrow(
            "SELECT * FROM student_quests WHERE student_id = $1 AND quest_id = $2",
            student_id, quest_id,
        )
        return StudentQuestEntity(**dict(row)) if row else None

    async def create(
        self, student_id: UUID, quest_id: UUID, total_count: int
    ) -> StudentQuestEntity:
        row = await self.conn.fetchrow(
            """INSERT INTO student_quests (student_id, quest_id, total_count)
               VALUES ($1, $2, $3) RETURNING *""",
            student_id, quest_id, total_count,
        )
        return StudentQuestEntity(**dict(row))

    async def advance(self, sq_id: UUID, is_correct: bool) -> StudentQuestEntity:
        if is_correct:
            row = await self.conn.fetchrow(
                """UPDATE student_quests
                   SET current_q = current_q + 1,
                       correct_count = correct_count + 1,
                       current_question_id = NULL,
                       current_difficulty_level = NULL
                   WHERE id = $1 RETURNING *""",
                sq_id,
            )
        else:
            row = await self.conn.fetchrow(
                """UPDATE student_quests
                   SET current_q = current_q + 1,
                       current_question_id = NULL,
                       current_difficulty_level = NULL
                   WHERE id = $1 RETURNING *""",
                sq_id,
            )
        return StudentQuestEntity(**dict(row))

    async def set_current_question(
        self,
        sq_id: UUID,
        question_id: UUID,
        difficulty_level: str,
    ) -> StudentQuestEntity:
        row = await self.conn.fetchrow(
            """UPDATE student_quests
               SET current_question_id = $2,
                   current_difficulty_level = $3
               WHERE id = $1
               RETURNING *""",
            sq_id,
            question_id,
            difficulty_level,
        )
        return StudentQuestEntity(**dict(row))

    async def advance_adaptive(
        self,
        sq_id: UUID,
        is_correct: bool,
        next_question_id: Optional[UUID],
        next_difficulty_level: Optional[str],
    ) -> StudentQuestEntity:
        if is_correct:
            row = await self.conn.fetchrow(
                """UPDATE student_quests
                   SET current_q = current_q + 1,
                       correct_count = correct_count + 1,
                       current_question_id = $2,
                       current_difficulty_level = $3
                   WHERE id = $1 RETURNING *""",
                sq_id,
                next_question_id,
                next_difficulty_level,
            )
        else:
            row = await self.conn.fetchrow(
                """UPDATE student_quests
                   SET current_q = current_q + 1,
                       current_question_id = $2,
                       current_difficulty_level = $3
                   WHERE id = $1 RETURNING *""",
                sq_id,
                next_question_id,
                next_difficulty_level,
            )
        return StudentQuestEntity(**dict(row))

    async def complete(self, sq_id: UUID) -> Optional[StudentQuestEntity]:
        row = await self.conn.fetchrow(
            """UPDATE student_quests
               SET status = 'completed', finished_at = NOW()
               WHERE id = $1 AND status = 'in_progress'
               RETURNING *""",
            sq_id,
        )
        return StudentQuestEntity(**dict(row)) if row else None

    async def list_by_student(self, student_id: UUID) -> List[dict]:
        rows = await self.conn.fetch(
            """SELECT sq.*,
                      q.title AS quest_title,
                      q.description AS quest_description,
                      q.xp_reward AS quest_xp_reward
               FROM student_quests sq
               JOIN quests q ON q.id = sq.quest_id
               WHERE sq.student_id = $1
               ORDER BY sq.started_at DESC""",
            student_id,
        )
        return [dict(r) for r in rows]
