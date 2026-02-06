from typing import List
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends

from app.database import get_db
from app.auth.dependencies import require_teacher
from app.entities.user import UserEntity
from app.services.quest_service import QuestService
from app.services.group_service import GroupService
from app.services.user_service import UserService
from app.repositories.question_repository import QuestionRepository
from app.dtos.quest_dtos import QuestCreate, QuestUpdate, QuestResponse
from app.dtos.question_dtos import QuestionCreate, QuestionFullResponse
from app.dtos.group_dtos import GroupCreate, GroupResponse, GroupDetailResponse
from app.dtos.user_dtos import UserCreate, UserResponse

router = APIRouter(prefix="/teacher", tags=["teacher"])


@router.post("/quests", response_model=QuestResponse)
async def create_quest(
    body: QuestCreate,
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    return await QuestService(conn).create_quest(
        body.title, body.description, body.xp_reward, user.id
    )


@router.get("/quests", response_model=List[QuestResponse])
async def my_quests(
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    return await QuestService(conn).list_teacher_quests(user.id)


@router.patch("/quests/{quest_id}", response_model=QuestResponse)
async def update_quest(
    quest_id: UUID, body: QuestUpdate,
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    return await QuestService(conn).update_quest(
        quest_id, title=body.title, description=body.description,
        xp_reward=body.xp_reward, is_active=body.is_active,
    )


@router.post("/quests/{quest_id}/questions", response_model=QuestionFullResponse)
async def add_question(
    quest_id: UUID, body: QuestionCreate,
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    entity = await QuestionRepository(conn).create(
        quest_id, body.text, body.option_a, body.option_b,
        body.option_c, body.option_d, body.correct, body.sort_order,
    )
    return QuestionFullResponse(**entity.model_dump())


@router.get("/quests/{quest_id}/questions", response_model=List[QuestionFullResponse])
async def list_questions(
    quest_id: UUID,
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    entities = await QuestionRepository(conn).list_by_quest(quest_id)
    return [QuestionFullResponse(**e.model_dump()) for e in entities]


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: UUID,
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    deleted = await QuestionRepository(conn).delete(question_id)
    return {"deleted": deleted}


@router.post("/groups", response_model=GroupResponse)
async def create_group(
    body: GroupCreate,
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    return await GroupService(conn).create_group(body.name, user.id)


@router.get("/groups", response_model=List[GroupResponse])
async def my_groups(
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    # только свои группы
    return await GroupService(conn).list_groups_for_teacher(user.id)


@router.get("/groups/{group_id}", response_model=GroupDetailResponse)
async def get_group(
    group_id: UUID,
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    return await GroupService(conn).get_group_detail(group_id)


@router.post("/groups/{group_id}/students/{student_id}")
async def add_student_to_group(
    group_id: UUID, student_id: UUID,
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    await GroupService(conn).add_student(group_id, student_id)
    return {"ok": True}


@router.delete("/groups/{group_id}/students/{student_id}")
async def remove_student_from_group(
    group_id: UUID, student_id: UUID,
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    await GroupService(conn).remove_student(group_id, student_id)
    return {"ok": True}


@router.post("/students", response_model=UserResponse)
async def create_student(
    body: UserCreate,
    user: UserEntity = Depends(require_teacher),
    conn: asyncpg.Connection = Depends(get_db),
):
    entity = await UserService(conn).create_user(
        body.name, body.surname, body.username, body.password, "student"
    )
    return UserResponse(**entity.model_dump())