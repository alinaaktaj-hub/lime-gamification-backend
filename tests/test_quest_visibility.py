import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.student_router import get_quest, get_quest_questions, list_quests
from app.repositories.question_repository import QuestionRepository
from app.repositories.student_quest_repository import StudentQuestRepository
from app.services.quest_service import QuestService


def test_get_visible_quest_rejects_unassigned_or_inactive_quest():
    quest_id = uuid4()
    student_id = uuid4()
    service = QuestService(None)

    async def find_active_for_student(requested_student_id, requested_id):
        return None

    service.quest_repo = SimpleNamespace(
        find_active_for_student=find_active_for_student,
        get_question_count=lambda requested_id: 0,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.get_visible_quest(student_id, quest_id))

    assert exc.value.status_code == 404


def test_student_list_route_uses_student_visibility(monkeypatch):
    called = {"student_id": None}

    async def fake_list_visible_quests(self, student_id):
        called["student_id"] = student_id
        return []

    monkeypatch.setattr(QuestService, "list_visible_quests", fake_list_visible_quests)
    student = SimpleNamespace(id=uuid4(), role="student")
    asyncio.run(list_quests(user=student, conn=None))

    assert called["student_id"] == student.id


def test_student_get_route_rejects_unassigned_quest(monkeypatch):
    async def fake_get_visible_quest(self, student_id, quest_id):
        raise HTTPException(status_code=404, detail="Quest not found or inactive")

    monkeypatch.setattr(QuestService, "get_visible_quest", fake_get_visible_quest)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            get_quest(
                uuid4(),
                user=SimpleNamespace(id=uuid4(), role="student"),
                conn=None,
            )
        )

    assert exc.value.status_code == 404


def test_student_question_route_rejects_unassigned_quest(monkeypatch):
    async def fake_get_visible_quest(self, student_id, quest_id):
        raise HTTPException(status_code=404, detail="Quest not found or inactive")

    monkeypatch.setattr(QuestService, "get_visible_quest", fake_get_visible_quest)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            get_quest_questions(
                uuid4(),
                user=SimpleNamespace(id=uuid4(), role="student"),
                conn=None,
            )
        )

    assert exc.value.status_code == 404


def test_student_question_route_returns_only_current_question_for_adaptive_quest(monkeypatch):
    question_id = uuid4()
    quest_id = uuid4()

    async def fake_get_visible_quest(self, student_id, requested_quest_id):
        return SimpleNamespace(id=requested_quest_id, delivery_mode="adaptive")

    async def fake_find_active(self, student_id, requested_quest_id):
        return SimpleNamespace(current_question_id=question_id)

    async def fake_find_by_id(self, requested_question_id):
        return SimpleNamespace(
            id=requested_question_id,
            quest_id=quest_id,
            text="Adaptive question",
            option_a="A",
            option_b="B",
            option_c=None,
            option_d=None,
            sort_order=0,
        )

    monkeypatch.setattr(QuestService, "get_visible_quest", fake_get_visible_quest)
    monkeypatch.setattr(StudentQuestRepository, "find_active", fake_find_active)
    monkeypatch.setattr(QuestionRepository, "find_by_id", fake_find_by_id)

    result = asyncio.run(
        get_quest_questions(
            quest_id,
            user=SimpleNamespace(id=uuid4(), role="student"),
            conn=None,
        )
    )

    assert len(result) == 1
    assert result[0].id == question_id
