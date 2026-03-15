from typing import Optional
from uuid import UUID

import asyncpg
from fastapi import HTTPException, status

from app.auth.security import verify_password, create_access_token
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, conn: asyncpg.Connection):
        self.user_repo = UserRepository(conn)

    async def authenticate(self, username: str, password: str) -> Optional[str]:
        user = await self.user_repo.find_by_username(username)
        if not user or not verify_password(password, user.hashed_password):
            return None
        if user.must_change_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "password_change_required",
                    "message": "Password change required",
                },
            )
        return create_access_token({"sub": str(user.id), "role": user.role})

    async def get_me(self, user_id: UUID) -> Optional[dict]:
        user = await self.user_repo.find_by_id(user_id)
        if not user:
            return None
        result = {
            "id": user.id, "name": user.name, "surname": user.surname,
            "username": user.username, "role": user.role,
        }
        if user.role == "student":
            sd = await self.user_repo.get_student_data(user.id)
            if sd:
                result["total_xp"] = sd.total_xp
                result["level"] = sd.level
        return result
