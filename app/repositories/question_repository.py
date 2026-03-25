from typing import Optional, List
from uuid import UUID

import asyncpg

from app.entities.question import QuestionEntity


class QuestionRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create(
        self, quest_id: UUID, text: str,
        option_a: str, option_b: str,
        option_c: Optional[str], option_d: Optional[str],
        correct: str, sort_order: int
    ) -> QuestionEntity:
        row = await self.conn.fetchrow(
            """INSERT INTO questions
                   (quest_id, text, option_a, option_b, option_c, option_d,
                    correct, sort_order)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
               RETURNING *""",
            quest_id, text, option_a, option_b, option_c, option_d,
            correct, sort_order,
        )
        return QuestionEntity(**dict(row))

    async def list_by_quest(self, quest_id: UUID) -> List[QuestionEntity]:
        rows = await self.conn.fetch(
            "SELECT * FROM questions WHERE quest_id = $1 ORDER BY sort_order, id",
            quest_id,
        )
        return [QuestionEntity(**dict(r)) for r in rows]

    async def find_by_id(self, question_id: UUID) -> Optional[QuestionEntity]:
        row = await self.conn.fetchrow(
            "SELECT * FROM questions WHERE id = $1", question_id
        )
        return QuestionEntity(**dict(row)) if row else None

    async def find_quest_id(self, question_id: UUID) -> Optional[UUID]:
        return await self.conn.fetchval(
            "SELECT quest_id FROM questions WHERE id = $1",
            question_id,
        )

    async def delete(self, question_id: UUID) -> bool:
        result = await self.conn.execute(
            "DELETE FROM questions WHERE id = $1", question_id
        )
        return result == "DELETE 1"
