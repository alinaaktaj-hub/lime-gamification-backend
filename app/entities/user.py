from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class UserEntity(BaseModel):
    id: UUID
    name: str
    surname: str
    username: str
    hashed_password: str
    role: str
    must_change_password: bool = True
    created_at: datetime


class StudentDataEntity(BaseModel):
    user_id: UUID
    total_xp: int
    level: int
