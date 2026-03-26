from datetime import datetime
from typing import Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, model_validator


DifficultyLevel = Literal["easy", "medium", "hard"]


class QuestionCreate(BaseModel):
    text: str
    option_a: str
    option_b: str
    option_c: Optional[str] = None
    option_d: Optional[str] = None
    correct: Literal["A", "B", "C", "D"]
    sort_order: int = 0
    difficulty_level: Optional[DifficultyLevel] = None
    difficulty_score: Optional[float] = Field(default=None, ge=0, le=1)
    difficulty_rationale: Optional[str] = None
    difficulty_scored_at: Optional[datetime] = None
    difficulty_model_version: Optional[str] = None
    difficulty_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    difficulty_needs_review: bool = True

    @model_validator(mode="after")
    def validate_matching_option(self):
        if self.correct == "C" and not self.option_c:
            raise ValueError("option_c is required when correct answer is C")
        if self.correct == "D" and not self.option_d:
            raise ValueError("option_d is required when correct answer is D")
        return self


class QuestionUpdate(BaseModel):
    difficulty_level: Optional[DifficultyLevel] = None
    difficulty_score: Optional[float] = Field(default=None, ge=0, le=1)
    difficulty_rationale: Optional[str] = None
    difficulty_scored_at: Optional[datetime] = None
    difficulty_model_version: Optional[str] = None
    difficulty_confidence: Optional[float] = Field(default=None, ge=0, le=1)
    difficulty_needs_review: Optional[bool] = None


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
    difficulty_level: Optional[DifficultyLevel] = None
    difficulty_score: Optional[float] = None
    difficulty_rationale: Optional[str] = None
    difficulty_scored_at: Optional[datetime] = None
    difficulty_model_version: Optional[str] = None
    difficulty_confidence: Optional[float] = None
    difficulty_needs_review: bool = True


class AnswerRequest(BaseModel):
    quest_id: UUID
    answer: str
    question_id: Optional[UUID] = None


class AnswerResponse(BaseModel):
    correct: bool
    correct_answer: str
    is_last_question: bool
    current_q: int
    correct_count: int
    total_count: int
    explanation: Optional[str] = None
    next_difficulty_level: Optional[DifficultyLevel] = None
    adaptation_action: Optional[str] = None
    adaptation_reason: Optional[str] = None
    next_question: Optional[QuestionResponse] = None
