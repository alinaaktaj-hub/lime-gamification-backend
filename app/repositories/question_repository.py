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
        correct: str, sort_order: int,
        difficulty_level: Optional[str] = None,
        difficulty_score: Optional[float] = None,
        difficulty_rationale: Optional[str] = None,
        difficulty_scored_at=None,
        difficulty_model_version: Optional[str] = None,
        difficulty_confidence: Optional[float] = None,
        difficulty_needs_review: bool = True,
    ) -> QuestionEntity:
        row = await self.conn.fetchrow(
            """INSERT INTO questions
                   (quest_id, text, option_a, option_b, option_c, option_d,
                    correct, sort_order, difficulty_level, difficulty_score,
                    difficulty_rationale, difficulty_scored_at,
                    difficulty_model_version, difficulty_confidence,
                    difficulty_needs_review)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
               RETURNING *""",
            quest_id, text, option_a, option_b, option_c, option_d,
            correct, sort_order, difficulty_level, difficulty_score,
            difficulty_rationale, difficulty_scored_at, difficulty_model_version,
            difficulty_confidence, difficulty_needs_review,
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

    async def update_metadata(self, question_id: UUID, **fields) -> Optional[QuestionEntity]:
        fields = {key: value for key, value in fields.items() if value is not None}
        if not fields:
            return await self.find_by_id(question_id)
        sets = ", ".join(f"{key} = ${index + 2}" for index, key in enumerate(fields))
        row = await self.conn.fetchrow(
            f"UPDATE questions SET {sets} WHERE id = $1 RETURNING *",
            question_id,
            *fields.values(),
        )
        return QuestionEntity(**dict(row)) if row else None
