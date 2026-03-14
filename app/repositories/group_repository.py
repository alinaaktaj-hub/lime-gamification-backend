from typing import Optional, List
from uuid import UUID

import asyncpg

from app.entities.group import GroupEntity


class GroupRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def create(self, name: str, teacher_id: UUID) -> GroupEntity:
        row = await self.conn.fetchrow(
            "INSERT INTO groups (name, teacher_id) VALUES ($1, $2) RETURNING *",
            name, teacher_id,
        )
        return GroupEntity(**dict(row))

    async def find_by_id(self, group_id: UUID) -> Optional[GroupEntity]:
        row = await self.conn.fetchrow(
            "SELECT * FROM groups WHERE id = $1", group_id
        )
        return GroupEntity(**dict(row)) if row else None

    async def list_by_teacher(self, teacher_id: UUID) -> List[GroupEntity]:
        rows = await self.conn.fetch(
            "SELECT * FROM groups WHERE teacher_id = $1 ORDER BY created_at",
            teacher_id,
        )
        return [GroupEntity(**dict(r)) for r in rows]

    async def list_all(self) -> List[GroupEntity]:
        rows = await self.conn.fetch("SELECT * FROM groups ORDER BY created_at")
        return [GroupEntity(**dict(r)) for r in rows]

    async def add_student(self, group_id: UUID, student_id: UUID) -> bool:
        result = await self.conn.execute(
            """INSERT INTO group_students (group_id, student_id)
               VALUES ($1, $2) ON CONFLICT DO NOTHING""",
            group_id, student_id,
        )
        return result == "INSERT 0 1"

    async def remove_student(self, group_id: UUID, student_id: UUID) -> bool:
        result = await self.conn.execute(
            "DELETE FROM group_students WHERE group_id=$1 AND student_id=$2",
            group_id, student_id,
        )
        return result == "DELETE 1"

    async def get_students(self, group_id: UUID) -> List[dict]:
        rows = await self.conn.fetch(
            """SELECT u.id, u.name, u.surname, u.username, u.role, u.created_at,
                      COALESCE(sd.total_xp, 0) as total_xp,
                      COALESCE(sd.level, 1) as level
               FROM group_students gs
               JOIN users u ON u.id = gs.student_id
               LEFT JOIN student_data sd ON sd.user_id = u.id
               WHERE gs.group_id = $1
               ORDER BY u.surname, u.name""",
            group_id,
        )
        return [dict(r) for r in rows]

    async def get_student_count(self, group_id: UUID) -> int:
        return await self.conn.fetchval(
            "SELECT COUNT(*) FROM group_students WHERE group_id = $1", group_id
        )
