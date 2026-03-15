import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.student_router import get_quest_questions
from app.services.quest_service import QuestService


def test_get_quest_rejects_inactive_quest():
    quest_id = uuid4()
    service = QuestService(None)

    async def find_by_id(requested_id):
        return SimpleNamespace(
            id=requested_id,
            title="Inactive",
            description=None,
            xp_reward=10,
            teacher_id=uuid4(),
            is_active=False,
            created_at=None,
        )

    service.quest_repo = SimpleNamespace(
        find_by_id=find_by_id,
        get_question_count=lambda requested_id: 0,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.get_quest(quest_id))

    assert exc.value.status_code == 404


def test_student_question_route_rejects_inactive_quest(monkeypatch):
    async def fake_get_quest(self, quest_id):
        raise HTTPException(status_code=404, detail="Quest not found or inactive")

    monkeypatch.setattr(QuestService, "get_quest", fake_get_quest)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            get_quest_questions(
                uuid4(),
                user=SimpleNamespace(id=uuid4(), role="student"),
                conn=None,
            )
        )

    assert exc.value.status_code == 404
