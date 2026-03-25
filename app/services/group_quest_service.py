from typing import List
from uuid import UUID

import asyncpg
from fastapi import HTTPException

from app.dtos.group_dtos import GroupQuestResponse
from app.repositories.group_quest_repository import GroupQuestRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.quest_repository import QuestRepository


class GroupQuestService:
    def __init__(self, conn: asyncpg.Connection):
        self.group_repo = GroupRepository(conn)
        self.quest_repo = QuestRepository(conn)
        self.group_quest_repo = GroupQuestRepository(conn)

    async def _require_owned_group(self, group_id: UUID, teacher_id: UUID):
        group = await self.group_repo.find_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        if group.teacher_id != teacher_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    async def _require_owned_quest(self, quest_id: UUID, teacher_id: UUID):
        quest = await self.quest_repo.find_by_id(quest_id)
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")
        if quest.teacher_id != teacher_id:
            raise HTTPException(status_code=403, detail="Forbidden")

    async def assign_quest_to_group(self, group_id: UUID, quest_id: UUID, teacher_id: UUID):
        await self._require_owned_group(group_id, teacher_id)
        await self._require_owned_quest(quest_id, teacher_id)
        inserted = await self.group_quest_repo.assign(group_id, quest_id)
        if not inserted:
            raise HTTPException(status_code=409, detail="Quest already assigned")

    async def unassign_quest_from_group(
        self, group_id: UUID, quest_id: UUID, teacher_id: UUID
    ):
        await self._require_owned_group(group_id, teacher_id)
        await self._require_owned_quest(quest_id, teacher_id)
        await self.group_quest_repo.unassign(group_id, quest_id)

    async def list_group_quests(
        self, group_id: UUID, teacher_id: UUID
    ) -> List[GroupQuestResponse]:
        await self._require_owned_group(group_id, teacher_id)
        rows = await self.group_quest_repo.list_group_quests(group_id)
        for row in rows:
            if row["teacher_id"] != teacher_id:
                raise HTTPException(status_code=403, detail="Forbidden")
        return [GroupQuestResponse(**row) for row in rows]
