from typing import List
from uuid import UUID

import asyncpg
from fastapi import HTTPException

from app.repositories.group_repository import GroupRepository
from app.repositories.user_repository import UserRepository
from app.dtos.group_dtos import GroupResponse, GroupDetailResponse
from app.dtos.user_dtos import StudentResponse


class GroupService:
    def __init__(self, conn: asyncpg.Connection):
        self.group_repo = GroupRepository(conn)
        self.user_repo = UserRepository(conn)

    async def create_group(self, name: str, teacher_id: UUID) -> GroupResponse:
        entity = await self.group_repo.create(name, teacher_id)
        return GroupResponse(**entity.model_dump(), student_count=0)

    async def list_groups_for_teacher(self, teacher_id: UUID) -> List[GroupResponse]:
        groups = await self.group_repo.list_by_teacher(teacher_id)
        result = []
        for g in groups:
            count = await self.group_repo.get_student_count(g.id)
            result.append(GroupResponse(**g.model_dump(), student_count=count))
        return result

    async def list_all_groups(self) -> List[GroupResponse]:
        groups = await self.group_repo.list_all()
        result = []
        for g in groups:
            count = await self.group_repo.get_student_count(g.id)
            result.append(GroupResponse(**g.model_dump(), student_count=count))
        return result

    async def get_group_detail(
        self, group_id: UUID, teacher_id: UUID = None
    ) -> GroupDetailResponse:
        group = await self.group_repo.find_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        if teacher_id is not None and group.teacher_id != teacher_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        students_raw = await self.group_repo.get_students(group_id)
        students = [StudentResponse(**s) for s in students_raw]
        return GroupDetailResponse(
            id=group.id, name=group.name, teacher_id=group.teacher_id,
            created_at=group.created_at, students=students,
        )

    async def add_student(self, group_id: UUID, student_id: UUID, teacher_id: UUID):
        group = await self.group_repo.find_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        if group.teacher_id != teacher_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        student = await self.user_repo.find_by_id(student_id)
        if not student:
            raise HTTPException(status_code=400, detail="Student not found")
        if student.role != "student":
            raise HTTPException(status_code=400, detail="Target user must be a student")
        try:
            await self.group_repo.add_student(group_id, student_id)
        except asyncpg.ForeignKeyViolationError:
            raise HTTPException(status_code=400, detail="Student not found")

    async def remove_student(self, group_id: UUID, student_id: UUID, teacher_id: UUID):
        group = await self.group_repo.find_by_id(group_id)
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
        if group.teacher_id != teacher_id:
            raise HTTPException(status_code=403, detail="Forbidden")
        await self.group_repo.remove_student(group_id, student_id)
