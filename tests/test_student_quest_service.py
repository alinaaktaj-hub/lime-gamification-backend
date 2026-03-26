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


def test_answer_question_records_answer_event():
    student_id = uuid4()
    quest_id = uuid4()
    sq_id = uuid4()
    question_id = uuid4()
    recorded = {}

    service = StudentQuestService(None)

    async def find_active(requested_student_id, requested_quest_id):
        return SimpleNamespace(
            id=sq_id,
            student_id=requested_student_id,
            quest_id=requested_quest_id,
            current_q=0,
            total_count=1,
            correct_count=0,
        )

    async def list_by_quest(requested_quest_id):
        return [SimpleNamespace(id=question_id, correct="A")]

    async def advance(requested_sq_id, is_correct):
        return SimpleNamespace(
            id=requested_sq_id,
            current_q=1,
            correct_count=1,
            total_count=1,
        )

    async def record(**kwargs):
        recorded.update(kwargs)

    async def complete(*args, **kwargs):
        return None

    async def find_quest(requested_quest_id):
        return SimpleNamespace(id=requested_quest_id, delivery_mode="fixed")

    service.sq_repo = SimpleNamespace(find_active=find_active, advance=advance)
    service.quest_repo = SimpleNamespace(find_by_id=find_quest)
    service.question_repo = SimpleNamespace(list_by_quest=list_by_quest)
    service.answer_event_repo = SimpleNamespace(record=record)
    service._complete_quest = complete

    result = asyncio.run(service.answer_question(student_id, quest_id, "A"))

    assert result.correct is True
    assert recorded == {
        "student_id": student_id,
        "quest_id": quest_id,
        "question_id": question_id,
        "student_quest_id": sq_id,
        "question_index": 0,
        "submitted_answer": "A",
        "is_correct": True,
        "served_difficulty": None,
        "adaptation_action": None,
        "adaptation_reason": None,
    }


def test_start_adaptive_quest_selects_initial_medium_question():
    student_id = uuid4()
    quest_id = uuid4()
    sq_id = uuid4()
    medium_question = SimpleNamespace(id=uuid4(), difficulty_level="medium", difficulty_needs_review=False)
    hard_question = SimpleNamespace(id=uuid4(), difficulty_level="hard", difficulty_needs_review=False)

    service = StudentQuestService(None)

    async def find_active_for_student(requested_student_id, requested_quest_id):
        return SimpleNamespace(id=requested_quest_id, is_active=True, delivery_mode="adaptive")

    async def find_any(requested_student_id, requested_quest_id):
        return None

    async def get_question_count(qid):
        return 2

    async def create(student_id, quest_id, total_count):
        return SimpleNamespace(
            id=sq_id,
            student_id=student_id,
            quest_id=quest_id,
            current_q=0,
            correct_count=0,
            total_count=total_count,
            current_question_id=None,
            current_difficulty_level=None,
            status="in_progress",
            started_at=None,
            finished_at=None,
        )

    async def list_by_quest(requested_quest_id):
        return [hard_question, medium_question]

    async def set_current_question(requested_sq_id, question_id, difficulty_level):
        assert requested_sq_id == sq_id
        return SimpleNamespace(
            id=sq_id,
            student_id=student_id,
            quest_id=quest_id,
            current_q=0,
            correct_count=0,
            total_count=2,
            current_question_id=question_id,
            current_difficulty_level=difficulty_level,
            status="in_progress",
            started_at=None,
            finished_at=None,
        )

    service.quest_repo = SimpleNamespace(
        find_active_for_student=find_active_for_student,
        get_question_count=get_question_count,
    )
    service.sq_repo = SimpleNamespace(
        find_any=find_any,
        create=create,
        set_current_question=set_current_question,
    )
    service.question_repo = SimpleNamespace(list_by_quest=list_by_quest)

    result = asyncio.run(service.start_quest(student_id, quest_id))

    assert result.current_question_id == medium_question.id
    assert result.current_difficulty_level == "medium"


def test_answer_adaptive_question_records_selection_metadata():
    student_id = uuid4()
    quest_id = uuid4()
    sq_id = uuid4()
    current_question = SimpleNamespace(
        id=uuid4(),
        correct="A",
        difficulty_level="medium",
        difficulty_needs_review=False,
    )
    next_question = SimpleNamespace(
        id=uuid4(),
        quest_id=quest_id,
        text="Next",
        option_a="A",
        option_b="B",
        option_c=None,
        option_d=None,
        sort_order=1,
        difficulty_level="medium",
        difficulty_needs_review=False,
    )
    recorded = {}

    service = StudentQuestService(None)

    async def find_active(requested_student_id, requested_quest_id):
        return SimpleNamespace(
            id=sq_id,
            student_id=requested_student_id,
            quest_id=requested_quest_id,
            current_q=0,
            total_count=2,
            correct_count=0,
            current_question_id=current_question.id,
            current_difficulty_level="medium",
        )

    async def find_by_id(question_id):
        if question_id == current_question.id:
            return current_question
        return next_question

    async def list_by_quest(requested_quest_id):
        return [current_question, next_question]

    async def list_by_student_quest(student_quest_id):
        return []

    async def advance_adaptive(requested_sq_id, is_correct, next_question_id, next_difficulty_level):
        return SimpleNamespace(
            id=requested_sq_id,
            current_q=1,
            correct_count=1,
            total_count=2,
            current_question_id=next_question_id,
            current_difficulty_level=next_difficulty_level,
        )

    async def record(**kwargs):
        recorded.update(kwargs)

    async def find_quest(quest_id):
        return SimpleNamespace(id=quest_id, delivery_mode="adaptive")

    service.sq_repo = SimpleNamespace(find_active=find_active, advance_adaptive=advance_adaptive)
    service.quest_repo = SimpleNamespace(find_by_id=find_quest)
    service.question_repo = SimpleNamespace(find_by_id=find_by_id, list_by_quest=list_by_quest)
    service.answer_event_repo = SimpleNamespace(record=record, list_by_student_quest=list_by_student_quest)

    result = asyncio.run(service.answer_question(student_id, quest_id, "A", current_question.id))

    assert result.correct is True
    assert result.next_question.id == next_question.id
    assert result.next_difficulty_level == "medium"
    assert result.adaptation_action == "stay"
    assert result.explanation == "Correct. Difficulty stayed the same because recent answers were mixed."
    assert recorded["served_difficulty"] == "medium"
    assert recorded["adaptation_action"] == "stay"
