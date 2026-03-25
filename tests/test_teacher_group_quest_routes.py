import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.api.teacher_router import (
    assign_quest_to_group,
    list_group_quests,
    unassign_quest_from_group,
)
from app.dtos.group_dtos import GroupQuestResponse
from app.services.group_quest_service import GroupQuestService


def test_assign_group_quest_route_calls_service_and_returns_ok(monkeypatch):
    called = {"group_id": None, "quest_id": None, "teacher_id": None}
    group_id = uuid4()
    quest_id = uuid4()
    teacher_id = uuid4()

    async def fake_assign(self, gid, qid, tid):
        called["group_id"] = gid
        called["quest_id"] = qid
        called["teacher_id"] = tid

    monkeypatch.setattr(GroupQuestService, "assign_quest_to_group", fake_assign)

    result = asyncio.run(
        assign_quest_to_group(
            group_id=group_id,
            quest_id=quest_id,
            user=SimpleNamespace(id=teacher_id, role="teacher"),
            conn=None,
        )
    )

    assert result == {"ok": True}
    assert called == {
        "group_id": group_id,
        "quest_id": quest_id,
        "teacher_id": teacher_id,
    }


def test_list_group_quests_route_returns_service_data(monkeypatch):
    group_id = uuid4()
    teacher_id = uuid4()
    now = datetime.now(timezone.utc)

    async def fake_list(self, gid, tid):
        return [
            GroupQuestResponse(
                id=uuid4(),
                title="Quest",
                description=None,
                xp_reward=10,
                teacher_id=tid,
                is_active=True,
                created_at=now,
                question_count=1,
                assigned_at=now,
            )
        ]

    monkeypatch.setattr(GroupQuestService, "list_group_quests", fake_list)

    result = asyncio.run(
        list_group_quests(
            group_id=group_id,
            user=SimpleNamespace(id=teacher_id, role="teacher"),
            conn=None,
        )
    )

    assert len(result) == 1
    assert result[0].teacher_id == teacher_id


def test_unassign_group_quest_route_calls_service_and_returns_ok(monkeypatch):
    called = {"group_id": None, "quest_id": None, "teacher_id": None}
    group_id = uuid4()
    quest_id = uuid4()
    teacher_id = uuid4()

    async def fake_unassign(self, gid, qid, tid):
        called["group_id"] = gid
        called["quest_id"] = qid
        called["teacher_id"] = tid

    monkeypatch.setattr(GroupQuestService, "unassign_quest_from_group", fake_unassign)

    result = asyncio.run(
        unassign_quest_from_group(
            group_id=group_id,
            quest_id=quest_id,
            user=SimpleNamespace(id=teacher_id, role="teacher"),
            conn=None,
        )
    )

    assert result == {"ok": True}
    assert called == {
        "group_id": group_id,
        "quest_id": quest_id,
        "teacher_id": teacher_id,
    }
