from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel


class QuestEntity(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    xp_reward: int
    teacher_id: UUID
    delivery_mode: Literal["fixed", "adaptive"] = "fixed"
    is_active: bool
    created_at: datetime