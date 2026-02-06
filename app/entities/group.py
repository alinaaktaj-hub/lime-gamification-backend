from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class GroupEntity(BaseModel):
    id: UUID
    name: str
    teacher_id: UUID
    created_at: datetime