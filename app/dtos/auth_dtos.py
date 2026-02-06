from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: UUID
    name: str
    surname: str
    username: str
    role: str
    total_xp: Optional[int] = None
    level: Optional[int] = None