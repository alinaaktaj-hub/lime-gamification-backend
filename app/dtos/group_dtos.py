from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from app.dtos.user_dtos import StudentResponse


class GroupCreate(BaseModel):
    name: str


class GroupResponse(BaseModel):
    id: UUID
    name: str
    teacher_id: UUID
    created_at: datetime
    student_count: Optional[int] = None


class GroupDetailResponse(BaseModel):
    id: UUID
    name: str
    teacher_id: UUID
    created_at: datetime
    students: List[StudentResponse]


class GroupQuestResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    xp_reward: int
    teacher_id: UUID
    is_active: bool
    created_at: datetime
    question_count: int
    assigned_at: datetime
