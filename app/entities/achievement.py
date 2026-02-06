from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class AchievementEntity(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    quest_id: Optional[UUID]
    created_at: datetime