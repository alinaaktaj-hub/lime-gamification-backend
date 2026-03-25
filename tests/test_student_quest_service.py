import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.student_quest_service import StudentQuestService


class FakeTransaction:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        self.conn.tx_entered += 1
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self.conn.tx_exited += 1
        return False


class FakeConn:
    def __init__(self):
        self.tx_entered = 0
        self.tx_exited = 0

    def transaction(self):
        return FakeTransaction(self)


def test_finish_quest_requires_all_questions_answered():
    service = StudentQuestService(FakeConn())
    service.sq_repo = SimpleNamespace(
        find_active=lambda student_id, quest_id: None
    )

    async def fake_find_active(student_id, quest_id):
        return SimpleNamespace(
            id=uuid4(),
            student_id=student_id,
            quest_id=quest_id,
            current_q=1,
            total_count=3,
        )

    service.sq_repo.find_active = fake_find_active

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.finish_quest(uuid4(), uuid4()))

    assert exc.value.status_code == 400
    assert "questions" in exc.value.detail.lower()


def test_complete_quest_is_wrapped_in_transaction():
    conn = FakeConn()
    service = StudentQuestService(conn)

    async def complete(sq_id):
        return SimpleNamespace(id=sq_id)

    async def find_quest(quest_id):
        return SimpleNamespace(id=quest_id, xp_reward=75)

    async def update_student_xp(student_id, xp_to_add):
        return SimpleNamespace(total_xp=175, level=2)

    async def find_achievement(quest_id):
        return None

    service.sq_repo = SimpleNamespace(complete=complete)
    service.quest_repo = SimpleNamespace(find_by_id=find_quest)
    service.user_repo = SimpleNamespace(update_student_xp=update_student_xp)
    service.achievement_repo = SimpleNamespace(
        find_by_quest=find_achievement,
        has_achievement=lambda student_id, achievement_id: False,
        award=lambda student_id, achievement_id: None,
    )

    result = asyncio.run(service._complete_quest(uuid4(), uuid4(), uuid4()))

    assert conn.tx_entered == 1
    assert conn.tx_exited == 1
    assert result.xp_earned == 75
    assert result.total_xp == 175


def test_complete_quest_prevents_double_award():
    conn = FakeConn()
    service = StudentQuestService(conn)
    update_calls = {"count": 0}

    async def complete(sq_id):
        return None

    async def find_quest(quest_id):
        return SimpleNamespace(id=quest_id, xp_reward=30)

    async def update_student_xp(student_id, xp_to_add):
        update_calls["count"] += 1
        return SimpleNamespace(total_xp=130, level=2)

    service.sq_repo = SimpleNamespace(complete=complete)
    service.quest_repo = SimpleNamespace(find_by_id=find_quest)
    service.user_repo = SimpleNamespace(update_student_xp=update_student_xp)

    async def find_achievement(quest_id):
        return None

    service.achievement_repo = SimpleNamespace(
        find_by_quest=find_achievement,
        has_achievement=lambda student_id, achievement_id: False,
        award=lambda student_id, achievement_id: None,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service._complete_quest(uuid4(), uuid4(), uuid4()))

    assert exc.value.status_code == 409
    assert update_calls["count"] == 0


def test_start_quest_rejects_unassigned_or_inactive_quest():
    student_id = uuid4()
    quest_id = uuid4()
    service = StudentQuestService(None)

    async def find_active_for_student(requested_student_id, requested_quest_id):
        return None

    service.quest_repo = SimpleNamespace(
        find_active_for_student=find_active_for_student
    )
    service.sq_repo = SimpleNamespace(
        find_any=lambda sid, qid: None,
        create=lambda sid, qid, total: None,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.start_quest(student_id, quest_id))

    assert exc.value.status_code == 404


def test_start_quest_keeps_already_started_409_behavior():
    student_id = uuid4()
    quest_id = uuid4()
    service = StudentQuestService(None)

    async def find_active_for_student(requested_student_id, requested_quest_id):
        return SimpleNamespace(id=requested_quest_id, is_active=True)

    async def find_any(requested_student_id, requested_quest_id):
        return SimpleNamespace(id=uuid4())

    service.quest_repo = SimpleNamespace(
        find_active_for_student=find_active_for_student,
        get_question_count=lambda qid: 2,
    )
    service.sq_repo = SimpleNamespace(
        find_any=find_any,
        create=lambda sid, qid, total: None,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.start_quest(student_id, quest_id))

    assert exc.value.status_code == 409


def test_start_quest_keeps_no_questions_400_behavior():
    student_id = uuid4()
    quest_id = uuid4()
    service = StudentQuestService(None)

    async def find_active_for_student(requested_student_id, requested_quest_id):
        return SimpleNamespace(id=requested_quest_id, is_active=True)

    async def find_any(requested_student_id, requested_quest_id):
        return None

    async def get_question_count(qid):
        return 0

    service.quest_repo = SimpleNamespace(
        find_active_for_student=find_active_for_student,
        get_question_count=get_question_count,
    )
    service.sq_repo = SimpleNamespace(
        find_any=find_any,
        create=lambda sid, qid, total: None,
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.start_quest(student_id, quest_id))

    assert exc.value.status_code == 400
    assert "no questions" in exc.value.detail.lower()
