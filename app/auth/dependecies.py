from uuid import UUID

import asyncpg
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt

from app.config import SECRET_KEY, ALGORITHM, security
from app.database import get_db
from app.entities.user import UserEntity
from app.repositories.user_repository import UserRepository


async def get_current_user(
    credentials=Depends(security),
    conn: asyncpg.Connection = Depends(get_db),
) -> UserEntity:
    err = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise err
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        raise err

    repo = UserRepository(conn)
    user = await repo.find_by_id(user_id)
    if user is None:
        raise err
    return user


async def require_student(user: UserEntity = Depends(get_current_user)) -> UserEntity:
    if user.role != "student":
        raise HTTPException(status_code=403, detail="Student access required")
    return user


async def require_teacher(user: UserEntity = Depends(get_current_user)) -> UserEntity:
    if user.role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    return user


async def require_admin(user: UserEntity = Depends(get_current_user)) -> UserEntity:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_teacher_or_admin(user: UserEntity = Depends(get_current_user)) -> UserEntity:
    if user.role not in ("teacher", "admin"):
        raise HTTPException(status_code=403, detail="Teacher or admin access required")
    return user