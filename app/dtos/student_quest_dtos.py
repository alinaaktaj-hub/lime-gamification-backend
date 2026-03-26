from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel

from app.dtos.question_dtos import QuestionResponse


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
    current_question_id: Optional[UUID] = None
    current_difficulty_level: Optional[Literal["easy", "medium", "hard"]] = None
    current_question: Optional[QuestionResponse] = None
    adaptation_action: Optional[str] = None
    adaptation_reason: Optional[str] = None
    status: str
    started_at: datetime
    finished_at: Optional[datetime]


class QuestCompleteResponse(BaseModel):
    xp_earned: int
    total_xp: int
    level: int
    achievement_earned: Optional[str] = None
