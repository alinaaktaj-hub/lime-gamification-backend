import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.entities.user import UserEntity
from app.services.auth_service import AuthService
from app.dtos.auth_dtos import (
    LoginRequest,
    TokenResponse,
    MeResponse,
    ChangePasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, conn: asyncpg.Connection = Depends(get_db)):
    service = AuthService(conn)
    token = await service.authenticate(body.username, body.password)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "invalid_credentials",
                "message": "Invalid username or password",
            },
        )
    return TokenResponse(access_token=token)


@router.get("/me", response_model=MeResponse)
async def me(
    user: UserEntity = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    service = AuthService(conn)
    result = await service.get_me(user.id)
    return MeResponse(**result)


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    body: ChangePasswordRequest,
    user: UserEntity = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db),
):
    service = AuthService(conn)
    updated = await service.change_password(user.id, body.new_password)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return MessageResponse(message="Password updated successfully")


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    conn: asyncpg.Connection = Depends(get_db),
):
    service = AuthService(conn)
    await service.request_password_reset(body.email)
    return MessageResponse(message="If an account exists, reset instructions were sent.")
