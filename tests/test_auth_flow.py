import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.auth_router import login
from app.dtos.auth_dtos import LoginRequest
from app.services.auth_service import AuthService


def test_authenticate_requires_password_change(monkeypatch):
    service = AuthService(None)

    async def find_by_username(username):
        return SimpleNamespace(
            id=uuid4(),
            role="student",
            hashed_password="hashed",
            must_change_password=True,
        )

    service.user_repo = SimpleNamespace(find_by_username=find_by_username)
    monkeypatch.setattr("app.services.auth_service.verify_password", lambda plain, hashed: True)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(service.authenticate("student", "secret"))

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "password_change_required"


def test_login_returns_machine_readable_invalid_credentials(monkeypatch):
    async def fake_authenticate(self, username, password):
        return None

    monkeypatch.setattr(AuthService, "authenticate", fake_authenticate)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(login(LoginRequest(username="student", password="bad"), conn=None))

    assert exc.value.status_code == 401
    assert exc.value.detail["code"] == "invalid_credentials"


def test_login_returns_token_when_authentication_succeeds(monkeypatch):
    async def fake_authenticate(self, username, password):
        return "token-123"

    monkeypatch.setattr(AuthService, "authenticate", fake_authenticate)

    result = asyncio.run(
        login(LoginRequest(username="student", password="good"), conn=None)
    )

    assert result.access_token == "token-123"
