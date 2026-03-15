import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.group_quest_service import GroupQuestService


def test_assign_quest_to_group_success():
    teacher_id = uuid4()
    group_id = uuid4()
    quest_id = uuid4()
    service = GroupQuestService(None)

    async def find_group(gid):
        return SimpleNamespace(id=gid, teacher_id=teacher_id)

    async def find_quest(qid):
        return SimpleNamespace(id=qid, teacher_id=teacher_id)

    async def assign(gid, qid):
        assert gid == group_id
        assert qid == quest_id
        return True

    service.group_repo = SimpleNamespace(find_by_id=find_group)
    service.quest_repo = SimpleNamespace(find_by_id=find_quest)
    service.group_quest_repo = SimpleNamespace(assign=assign)

    asyncio.run(service.assign_quest_to_group(group_id, quest_id, teacher_id))


def test_assign_quest_to_group_duplicate_returns_409():
    teacher_id = uuid4()
    group_id = uuid4()
    quest_id = uuid4()
    service = GroupQuestService(None)

    async def find_group(gid):
        return SimpleNamespace(id=gid, teacher_id=teacher_id)

    async def find_quest(qid):
        return SimpleNamespace(id=qid, teacher_id=teacher_id)

    async def assign(gid, qid):
        return False

    service.group_repo = SimpleNamespace(find_by_id=find_group)
    service.quest_repo = SimpleNamespace(find_by_id=find_quest)
    service.group_quest_repo = SimpleNamespace(assign=assign)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.assign_quest_to_group(group_id, quest_id, teacher_id))

    assert exc.value.status_code == 409


def test_assign_quest_to_group_rejects_non_owner_teacher():
    owner_id = uuid4()
    caller_id = uuid4()
    group_id = uuid4()
    quest_id = uuid4()
    service = GroupQuestService(None)

    async def find_group(gid):
        return SimpleNamespace(id=gid, teacher_id=owner_id)

    async def find_quest(qid):
        return SimpleNamespace(id=qid, teacher_id=caller_id)

    service.group_repo = SimpleNamespace(find_by_id=find_group)
    service.quest_repo = SimpleNamespace(find_by_id=find_quest)
    service.group_quest_repo = SimpleNamespace(assign=lambda gid, qid: True)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.assign_quest_to_group(group_id, quest_id, caller_id))

    assert exc.value.status_code == 403


def test_assign_quest_to_group_returns_404_when_group_missing():
    teacher_id = uuid4()
    group_id = uuid4()
    quest_id = uuid4()
    service = GroupQuestService(None)

    async def find_group(gid):
        return None

    service.group_repo = SimpleNamespace(find_by_id=find_group)
    service.quest_repo = SimpleNamespace(find_by_id=lambda qid: None)
    service.group_quest_repo = SimpleNamespace(assign=lambda gid, qid: True)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.assign_quest_to_group(group_id, quest_id, teacher_id))

    assert exc.value.status_code == 404


def test_list_group_quests_returns_assigned_quests_with_timestamp():
    teacher_id = uuid4()
    group_id = uuid4()
    quest_id = uuid4()
    assigned_at = datetime.now(timezone.utc)
    service = GroupQuestService(None)

    async def find_group(gid):
        return SimpleNamespace(id=gid, teacher_id=teacher_id)

    async def list_group_quests(gid):
        return [
            {
                "id": quest_id,
                "title": "Quest 1",
                "description": "d",
                "xp_reward": 25,
                "teacher_id": teacher_id,
                "is_active": True,
                "created_at": assigned_at,
                "question_count": 3,
                "assigned_at": assigned_at,
            }
        ]

    service.group_repo = SimpleNamespace(find_by_id=find_group)
    service.quest_repo = SimpleNamespace(find_by_id=lambda qid: None)
    service.group_quest_repo = SimpleNamespace(list_group_quests=list_group_quests)

    result = asyncio.run(service.list_group_quests(group_id, teacher_id))

    assert len(result) == 1
    assert result[0].id == quest_id
    assert result[0].assigned_at == assigned_at


def test_unassign_quest_from_group_is_idempotent_after_ownership_checks():
    teacher_id = uuid4()
    group_id = uuid4()
    quest_id = uuid4()
    service = GroupQuestService(None)

    async def find_group(gid):
        return SimpleNamespace(id=gid, teacher_id=teacher_id)

    async def find_quest(qid):
        return SimpleNamespace(id=qid, teacher_id=teacher_id)

    called = {"count": 0}

    async def unassign(gid, qid):
        called["count"] += 1
        return False

    service.group_repo = SimpleNamespace(find_by_id=find_group)
    service.quest_repo = SimpleNamespace(find_by_id=find_quest)
    service.group_quest_repo = SimpleNamespace(unassign=unassign)

    asyncio.run(service.unassign_quest_from_group(group_id, quest_id, teacher_id))

    assert called["count"] == 1


def test_list_group_quests_rejects_foreign_quest_rows():
    teacher_id = uuid4()
    foreign_teacher_id = uuid4()
    group_id = uuid4()
    assigned_at = datetime.now(timezone.utc)
    service = GroupQuestService(None)

    async def find_group(gid):
        return SimpleNamespace(id=gid, teacher_id=teacher_id)

    async def list_group_quests(gid):
        return [
            {
                "id": uuid4(),
                "title": "Quest 1",
                "description": "d",
                "xp_reward": 25,
                "teacher_id": foreign_teacher_id,
                "is_active": True,
                "created_at": assigned_at,
                "question_count": 3,
                "assigned_at": assigned_at,
            }
        ]

    service.group_repo = SimpleNamespace(find_by_id=find_group)
    service.quest_repo = SimpleNamespace(find_by_id=lambda qid: None)
    service.group_quest_repo = SimpleNamespace(list_group_quests=list_group_quests)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.list_group_quests(group_id, teacher_id))

    assert exc.value.status_code == 403
