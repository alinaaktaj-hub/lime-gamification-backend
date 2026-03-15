import asyncio
from types import SimpleNamespace
from uuid import uuid4

import asyncpg
import pytest
from fastapi import HTTPException

from app.services.group_service import GroupService


def test_get_group_detail_rejects_non_owner_teacher():
    group_id = uuid4()
    owner_id = uuid4()
    caller_id = uuid4()

    service = GroupService(None)

    async def find_group(gid):
        return SimpleNamespace(
            id=group_id,
            name="g1",
            teacher_id=owner_id,
            created_at=None,
        )

    service.group_repo = SimpleNamespace(
        find_by_id=find_group,
        get_students=lambda gid: [],
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.get_group_detail(group_id, caller_id))

    assert exc.value.status_code == 403


def test_add_student_returns_http_error_on_db_fk_failure():
    group_id = uuid4()
    teacher_id = uuid4()
    student_id = uuid4()

    service = GroupService(None)

    async def find_group(gid):
        return SimpleNamespace(id=group_id, teacher_id=teacher_id)

    async def add_student(gid, sid):
        raise asyncpg.ForeignKeyViolationError("student not found")

    service.group_repo = SimpleNamespace(
        find_by_id=find_group,
        add_student=add_student,
    )
    async def find_user(uid):
        return SimpleNamespace(id=uid, role="student")

    service.user_repo = SimpleNamespace(find_by_id=find_user)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.add_student(group_id, student_id, teacher_id))

    assert exc.value.status_code == 400


def test_add_student_rejects_non_student_user():
    group_id = uuid4()
    teacher_id = uuid4()
    target_user_id = uuid4()

    service = GroupService(None)

    async def find_group(gid):
        return SimpleNamespace(id=group_id, teacher_id=teacher_id)

    async def find_user(uid):
        return SimpleNamespace(id=uid, role="teacher")

    async def add_student(gid, sid):
        return True

    service.group_repo = SimpleNamespace(
        find_by_id=find_group,
        add_student=add_student,
    )
    service.user_repo = SimpleNamespace(find_by_id=find_user)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.add_student(group_id, target_user_id, teacher_id))

    assert exc.value.status_code == 400
    assert "student" in exc.value.detail.lower()


def test_add_student_allows_student_user():
    group_id = uuid4()
    teacher_id = uuid4()
    student_id = uuid4()
    called = {"value": False}

    service = GroupService(None)

    async def find_group(gid):
        return SimpleNamespace(id=group_id, teacher_id=teacher_id)

    async def find_user(uid):
        return SimpleNamespace(id=uid, role="student")

    async def add_student(gid, sid):
        called["value"] = True
        return True

    service.group_repo = SimpleNamespace(
        find_by_id=find_group,
        add_student=add_student,
    )
    service.user_repo = SimpleNamespace(find_by_id=find_user)

    asyncio.run(service.add_student(group_id, student_id, teacher_id))

    assert called["value"] is True
