from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class AchievementCreate(BaseModel):
    name: str
    description: Optional[str] = None
    quest_id: Optional[UUID] = None


class AchievementUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    quest_id: Optional[UUID] = None


class AchievementResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    quest_id: Optional[UUID]
    created_at: datetime


class StudentAchievementResponse(BaseModel):
    achievement_id: UUID
    name: str
    description: Optional[str]
    earned_at: datetime
