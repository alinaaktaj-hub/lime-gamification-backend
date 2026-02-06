from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    name: str
    surname: str
    username: str
    password: str = Field(min_length=4)
    role: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    surname: str
    username: str
    role: str
    created_at: datetime


class StudentResponse(BaseModel):
    id: UUID
    name: str
    surname: str
    username: str
    role: str
    total_xp: int
    level: int
    created_at: datetime