from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class StudentQuestResponse(BaseModel):
    id: UUID
    student_id: UUID
    quest_id: UUID
    quest_title: Optional[str] = None
    quest_description: Optional[str] = None
    quest_xp_reward: Optional[int] = None
    current_q: int
    correct_count: int
    total_count: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime]


class QuestCompleteResponse(BaseModel):
    xp_earned: int
    total_xp: int
    level: int
    achievement_earned: Optional[str] = None
