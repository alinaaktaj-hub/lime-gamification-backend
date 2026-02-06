from typing import List
from uuid import UUID

import asyncpg
from fastapi import HTTPException

from app.repositories.quest_repository import QuestRepository
from app.dtos.quest_dtos import QuestResponse


class QuestService:
    def __init__(self, conn: asyncpg.Connection):
        self.quest_repo = QuestRepository(conn)

    async def create_quest(
        self, title: str, description, xp_reward: int, teacher_id: UUID
    ) -> QuestResponse:
        entity = await self.quest_repo.create(title, description, xp_reward, teacher_id)
        return QuestResponse(**entity.model_dump(), question_count=0)

    async def list_active_quests(self) -> List[QuestResponse]:
        quests = await self.quest_repo.list_active()
        result = []
        for q in quests:
            count = await self.quest_repo.get_question_count(q.id)
            result.append(QuestResponse(**q.model_dump(), question_count=count))
        return result

    async def list_teacher_quests(self, teacher_id: UUID) -> List[QuestResponse]:
        quests = await self.quest_repo.list_by_teacher(teacher_id)
        result = []
        for q in quests:
            count = await self.quest_repo.get_question_count(q.id)
            result.append(QuestResponse(**q.model_dump(), question_count=count))
        return result

    async def get_quest(self, quest_id: UUID) -> QuestResponse:
        entity = await self.quest_repo.find_by_id(quest_id)
        if not entity:
            raise HTTPException(status_code=404, detail="Quest not found")
        count = await self.quest_repo.get_question_count(quest_id)
        return QuestResponse(**entity.model_dump(), question_count=count)

    async def update_quest(self, quest_id: UUID, **fields):
        fields = {k: v for k, v in fields.items() if v is not None}
        entity = await self.quest_repo.update(quest_id, **fields)
        if not entity:
            raise HTTPException(status_code=404, detail="Quest not found")
        count = await self.quest_repo.get_question_count(quest_id)
        return QuestResponse(**entity.model_dump(), question_count=count)