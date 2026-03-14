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

    async def is_owned_by(self, quest_id: UUID, teacher_id: UUID) -> bool:
        return await self.conn.fetchval(
            """SELECT EXISTS(
                 SELECT 1 FROM quests WHERE id = $1 AND teacher_id = $2
               )""",
            quest_id,
            teacher_id,
        )

    async def list_active(self) -> List[QuestEntity]:
        rows = await self.conn.fetch(
            "SELECT * FROM quests WHERE is_active = true ORDER BY created_at DESC"
        )
        return [QuestEntity(**dict(r)) for r in rows]

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
