from typing import Optional
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