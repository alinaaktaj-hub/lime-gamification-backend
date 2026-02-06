from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class QuestCreate(BaseModel):
    title: str
    description: Optional[str] = None
    xp_reward: int = 10


class QuestUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    xp_reward: Optional[int] = None
    is_active: Optional[bool] = None


class QuestResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    xp_reward: int
    teacher_id: UUID
    is_active: bool
    created_at: datetime
    question_count: Optional[int] = None