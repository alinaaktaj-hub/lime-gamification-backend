from typing import Optional, List
from uuid import UUID

import asyncpg

from app.entities.achievement import AchievementEntity


class AchievementRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create(
        self, name: str, description: Optional[str], quest_id: Optional[UUID]
    ) -> AchievementEntity:
        row = await self.conn.fetchrow(
            """INSERT INTO achievements (name, description, quest_id)
               VALUES ($1, $2, $3) RETURNING *""",
            name, description, quest_id,
        )
        return AchievementEntity(**dict(row))

    async def find_by_quest(self, quest_id: UUID) -> Optional[AchievementEntity]:
        row = await self.conn.fetchrow(
            "SELECT * FROM achievements WHERE quest_id = $1", quest_id
        )
        return AchievementEntity(**dict(row)) if row else None

    async def find_by_id(self, achievement_id: UUID) -> Optional[AchievementEntity]:
        row = await self.conn.fetchrow(
            "SELECT * FROM achievements WHERE id = $1", achievement_id
        )
        return AchievementEntity(**dict(row)) if row else None

    async def update(self, achievement_id: UUID, **fields) -> Optional[AchievementEntity]:
        if not fields:
            return await self.find_by_id(achievement_id)
        sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(fields))
        row = await self.conn.fetchrow(
            f"UPDATE achievements SET {sets} WHERE id = $1 RETURNING *",
            achievement_id, *fields.values(),
        )
        return AchievementEntity(**dict(row)) if row else None

    async def delete(self, achievement_id: UUID) -> bool:
        result = await self.conn.execute(
            "DELETE FROM achievements WHERE id = $1", achievement_id
        )
        return result == "DELETE 1"

    async def award(self, student_id: UUID, achievement_id: UUID) -> None:
        await self.conn.execute(
            """INSERT INTO student_achievements (student_id, achievement_id)
               VALUES ($1, $2) ON CONFLICT DO NOTHING""",
            student_id, achievement_id,
        )

    async def list_by_student(self, student_id: UUID) -> List[dict]:
        rows = await self.conn.fetch(
            """SELECT a.id as achievement_id, a.name, a.description, sa.earned_at
               FROM student_achievements sa
               JOIN achievements a ON a.id = sa.achievement_id
               WHERE sa.student_id = $1
               ORDER BY sa.earned_at DESC""",
            student_id,
        )
        return [dict(r) for r in rows]

    async def has_achievement(self, student_id: UUID, achievement_id: UUID) -> bool:
        return await self.conn.fetchval(
            """SELECT EXISTS(
                 SELECT 1 FROM student_achievements
                 WHERE student_id = $1 AND achievement_id = $2
               )""",
            student_id, achievement_id,
        )
