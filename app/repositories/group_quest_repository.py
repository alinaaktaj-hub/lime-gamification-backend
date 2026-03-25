from typing import List
from uuid import UUID

import asyncpg


class GroupQuestRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def assign(self, group_id: UUID, quest_id: UUID) -> bool:
        result = await self.conn.execute(
            """INSERT INTO group_quests (group_id, quest_id)
               VALUES ($1, $2)
               ON CONFLICT (group_id, quest_id) DO NOTHING""",
            group_id,
            quest_id,
        )
        return result == "INSERT 0 1"

    async def unassign(self, group_id: UUID, quest_id: UUID) -> bool:
        result = await self.conn.execute(
            "DELETE FROM group_quests WHERE group_id = $1 AND quest_id = $2",
            group_id,
            quest_id,
        )
        return result == "DELETE 1"

    async def list_group_quests(self, group_id: UUID) -> List[dict]:
        rows = await self.conn.fetch(
            """SELECT q.id,
                      q.title,
                      q.description,
                      q.xp_reward,
                      q.teacher_id,
                      q.is_active,
                      q.created_at,
                      COALESCE(qc.question_count, 0) AS question_count,
                      gq.assigned_at
               FROM group_quests gq
               JOIN quests q ON q.id = gq.quest_id
               LEFT JOIN (
                    SELECT quest_id, COUNT(*) AS question_count
                    FROM questions
                    GROUP BY quest_id
               ) qc ON qc.quest_id = q.id
               WHERE gq.group_id = $1
               ORDER BY gq.assigned_at DESC""",
            group_id,
        )
        return [dict(r) for r in rows]
