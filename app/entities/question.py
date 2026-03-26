from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel


class QuestionEntity(BaseModel):
    id: UUID
    quest_id: UUID
    text: str
    option_a: str
    option_b: str
    option_c: Optional[str]
    option_d: Optional[str]
    correct: str
    sort_order: int
    difficulty_level: Optional[Literal["easy", "medium", "hard"]] = None
    difficulty_score: Optional[float] = None
    difficulty_rationale: Optional[str] = None
    difficulty_scored_at: Optional[datetime] = None
    difficulty_model_version: Optional[str] = None
    difficulty_confidence: Optional[float] = None
    difficulty_needs_review: bool = True