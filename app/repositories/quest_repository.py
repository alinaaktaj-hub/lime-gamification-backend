from typing import Optional, List
from uuid import UUID

import asyncpg

from app.entities.quest import QuestEntity


class QuestRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create(
        self, title: str, description: Optional[str],
        xp_reward: int, teacher_id: UUID
    ) -> QuestEntity:
        row = await self.conn.fetchrow(
            """INSERT INTO quests (title, description, xp_reward, teacher_id)
               VALUES ($1, $2, $3, $4) RETURNING *""",
            title, description, xp_reward, teacher_id,
        )
        return QuestEntity(**dict(row))

    async def find_by_id(self, quest_id: UUID) -> Optional[QuestEntity]:
        row = await self.conn.fetchrow(
            "SELECT * FROM quests WHERE id = $1", quest_id
        )
        return QuestEntity(**dict(row)) if row else None

    async def list_active(self) -> List[QuestEntity]:
        rows = await self.conn.fetch(
            "SELECT * FROM quests WHERE is_active = true ORDER BY created_at DESC"
        )
        return [QuestEntity(**dict(r)) for r in rows]

    async def list_active_for_student(self, student_id: UUID) -> List[QuestEntity]:
        rows = await self.conn.fetch(
            """SELECT DISTINCT q.*
               FROM quests q
               JOIN groups g ON g.teacher_id = q.teacher_id
               JOIN group_students gs ON gs.group_id = g.id
               WHERE gs.student_id = $1 AND q.is_active = true
               ORDER BY q.created_at DESC""",
            student_id,
        )
        return [QuestEntity(**dict(r)) for r in rows]

    async def find_active_for_student(
        self, quest_id: UUID, student_id: UUID
    ) -> Optional[QuestEntity]:
        row = await self.conn.fetchrow(
            """SELECT q.*
               FROM quests q
               WHERE q.id = $1
                 AND q.is_active = true
                 AND EXISTS (
                    SELECT 1
                    FROM groups g
                    JOIN group_students gs ON gs.group_id = g.id
                    WHERE gs.student_id = $2
                      AND g.teacher_id = q.teacher_id
                 )""",
            quest_id, student_id,
        )
        return QuestEntity(**dict(row)) if row else None

    async def list_by_teacher(self, teacher_id: UUID) -> List[QuestEntity]:
        rows = await self.conn.fetch(
            "SELECT * FROM quests WHERE teacher_id = $1 ORDER BY created_at DESC",
            teacher_id,
        )
        return [QuestEntity(**dict(r)) for r in rows]

    async def update(self, quest_id: UUID, **fields) -> Optional[QuestEntity]:
        if not fields:
            return await self.find_by_id(quest_id)
        # хз что такое — динамически строим SET часть
        sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
        row = await self.conn.fetchrow(
            f"UPDATE quests SET {sets} WHERE id = $1 RETURNING *",
            quest_id, *fields.values(),
        )
        return QuestEntity(**dict(row)) if row else None

    async def get_question_count(self, quest_id: UUID) -> int:
        return await self.conn.fetchval(
            "SELECT COUNT(*) FROM questions WHERE quest_id = $1", quest_id
        )
