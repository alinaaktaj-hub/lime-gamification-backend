import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.entities.user import UserEntity
from app.services.auth_service import AuthService
from app.dtos.auth_dtos import LoginRequest, TokenResponse, MeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, conn: asyncpg.Connection = Depends(get_db)):
    service = AuthService(conn)
    token = await service.authenticate(body.username, body.password)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid username or password")
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
async def me(
    user: UserEntity = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    service = AuthService(conn)
    result = await service.get_me(user.id)
    return MeResponse(**result)