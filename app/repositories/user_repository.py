from typing import Optional, List
from uuid import UUID

import asyncpg

from app.entities.user import UserEntity, StudentDataEntity


class UserRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def find_by_username(self, username: str) -> Optional[UserEntity]:
        row = await self.conn.fetchrow(
            "SELECT * FROM users WHERE username = $1", username
        )
        return UserEntity(**dict(row)) if row else None

    async def find_by_id(self, user_id: UUID) -> Optional[UserEntity]:
        row = await self.conn.fetchrow(
            "SELECT * FROM users WHERE id = $1", user_id
        )
        return UserEntity(**dict(row)) if row else None

    async def create(
        self, name: str, surname: str, username: str,
        hashed_password: str, role: str
    ) -> UserEntity:
        row = await self.conn.fetchrow(
            """INSERT INTO users (name, surname, username, hashed_password, role)
               VALUES ($1, $2, $3, $4, $5)
               RETURNING *""",
            name, surname, username, hashed_password, role,
        )
        return UserEntity(**dict(row))

    async def get_student_data(self, user_id: UUID) -> Optional[StudentDataEntity]:
        row = await self.conn.fetchrow(
            "SELECT * FROM student_data WHERE user_id = $1", user_id
        )
        return StudentDataEntity(**dict(row)) if row else None

    async def create_student_data(self, user_id: UUID) -> StudentDataEntity:
        row = await self.conn.fetchrow(
            "INSERT INTO student_data (user_id) VALUES ($1) RETURNING *",
            user_id,
        )
        return StudentDataEntity(**dict(row))

    async def update_student_xp(self, user_id: UUID, xp_to_add: int) -> StudentDataEntity:
        # хз что такое — level считается как total_xp / 100 + 1
        row = await self.conn.fetchrow(
            """UPDATE student_data
               SET total_xp = total_xp + $2,
                   level = (total_xp + $2) / 100 + 1
               WHERE user_id = $1
               RETURNING *""",
            user_id, xp_to_add,
        )
        return StudentDataEntity(**dict(row))

    async def get_leaderboard(self, limit: int = 10) -> List[dict]:
        rows = await self.conn.fetch(
            """SELECT u.id, u.name, u.surname, u.username, u.role, u.created_at,
                      sd.total_xp, sd.level
               FROM users u
               JOIN student_data sd ON sd.user_id = u.id
               WHERE u.role = 'student'
               ORDER BY sd.total_xp DESC
               LIMIT $1""",
            limit,
        )
        return [dict(r) for r in rows]

    async def list_by_role(self, role: str) -> List[UserEntity]:
        rows = await self.conn.fetch(
            "SELECT * FROM users WHERE role = $1 ORDER BY created_at", role
        )
        return [UserEntity(**dict(r)) for r in rows]