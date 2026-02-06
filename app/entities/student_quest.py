from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class StudentQuestEntity(BaseModel):
    id: UUID
    student_id: UUID
    quest_id: UUID
    current_q: int
    correct_count: int
    total_count: int
    status: str
    started_at: datetime
    finished_at: Optional[datetime]