from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class QuestionCreate(BaseModel):
    text: str
    option_a: str
    option_b: str
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct: str
    sort_order: int = 0


class QuestionResponse(BaseModel):
    # для студентов — без correct
    id: UUID
    quest_id: UUID
    text: str
    option_a: str
    option_b: str
    option_c: Optional[str]
    option_d: Optional[str]
    sort_order: int


class QuestionFullResponse(BaseModel):
    # для учителей — с correct
    id: UUID
    quest_id: UUID
    text: str
    option_a: str
    option_b: str
    option_c: Optional[str]
    option_d: Optional[str]
    correct: str
    sort_order: int


class AnswerRequest(BaseModel):
    quest_id: UUID
    answer: str


class AnswerResponse(BaseModel):
    correct: bool
    correct_answer: str
    is_last_question: bool
    current_q: int
    correct_count: int
    total_count: int