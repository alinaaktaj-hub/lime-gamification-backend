import asyncpg
from fastapi import HTTPException, status

from app.auth.security import hash_password
from app.repositories.user_repository import UserRepository
from app.entities.user import UserEntity


class UserService:
    def __init__(self, conn: asyncpg.Connection):
        self.user_repo = UserRepository(conn)

    async def create_user(
        self, name: str, surname: str, username: str,
        password: str, role: str
    ) -> UserEntity:
        existing = await self.user_repo.find_by_username(username)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Username already taken")
        hashed = hash_password(password)
        user = await self.user_repo.create(name, surname, username, hashed, role)
        if role == "student":
            await self.user_repo.create_student_data(user.id)
        return user