from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel


class StudentQuestEntity(BaseModel):
    id: UUID
    student_id: UUID
    quest_id: UUID
    current_q: int
    correct_count: int
    total_count: int
    current_question_id: Optional[UUID] = None
    current_difficulty_level: Optional[Literal["easy", "medium", "hard"]] = None
    status: str
    started_at: datetime
    finished_at: Optional[datetime]