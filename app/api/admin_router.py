from typing import List

import asyncpg
from fastapi import APIRouter, Depends

from app.database import get_db
from app.auth.dependencies import require_admin
from app.entities.user import UserEntity
from app.services.user_service import UserService
from app.services.group_service import GroupService
from app.repositories.user_repository import UserRepository
from app.dtos.user_dtos import UserCreate, UserResponse
from app.dtos.group_dtos import GroupResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users", response_model=UserResponse)
async def create_user(
    body: UserCreate,
    user: UserEntity = Depends(require_admin),
    conn: asyncpg.Connection = Depends(get_db),
):
    entity = await UserService(conn).create_user(
        body.name, body.surname, body.username, body.password, body.role
    )
    return UserResponse(**entity.model_dump())


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    role: str = None,
    user: UserEntity = Depends(require_admin),
    conn: asyncpg.Connection = Depends(get_db),
):
    repo = UserRepository(conn)
    if role:
        entities = await repo.list_by_role(role)
    else:
        rows = await conn.fetch("SELECT * FROM users ORDER BY created_at")
        entities = [UserEntity(**dict(r)) for r in rows]
    return [UserResponse(**e.model_dump()) for e in entities]


@router.get("/groups", response_model=List[GroupResponse])
async def list_all_groups(
    user: UserEntity = Depends(require_admin),
    conn: asyncpg.Connection = Depends(get_db),
):
    # все группы всех учителей
    return await GroupService(conn).list_all_groups()