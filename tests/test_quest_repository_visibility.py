import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from app.repositories.quest_repository import QuestRepository


class FakeConn:
    def __init__(self):
        self.last_query = None
        self.last_args = None

    async def fetch(self, query, *args):
        self.last_query = query
        self.last_args = args
        now = datetime.now(timezone.utc)
        return [
            {
                "id": uuid4(),
                "title": "Quest",
                "description": None,
                "xp_reward": 10,
                "teacher_id": uuid4(),
                "is_active": True,
                "created_at": now,
            }
        ]

    async def fetchrow(self, query, *args):
        self.last_query = query
        self.last_args = args
        now = datetime.now(timezone.utc)
        return {
            "id": uuid4(),
            "title": "Quest",
            "description": None,
            "xp_reward": 10,
            "teacher_id": uuid4(),
            "is_active": True,
            "created_at": now,
        }


def test_list_active_for_student_uses_assignment_joins_and_distinct():
    conn = FakeConn()
    repo = QuestRepository(conn)
    student_id = uuid4()

    result = asyncio.run(repo.list_active_for_student(student_id))

    assert len(result) == 1
    query = (conn.last_query or "").lower()
    assert "distinct" in query
    assert "group_students" in query
    assert "group_quests" in query
    assert conn.last_args == (student_id,)


def test_find_active_for_student_filters_by_student_and_quest():
    conn = FakeConn()
    repo = QuestRepository(conn)
    student_id = uuid4()
    quest_id = uuid4()

    result = asyncio.run(repo.find_active_for_student(student_id, quest_id))

    assert result is not None
    query = (conn.last_query or "").lower()
    assert "group_students" in query
    assert "group_quests" in query
    assert "q.id = $2" in query
    assert conn.last_args == (student_id, quest_id)
