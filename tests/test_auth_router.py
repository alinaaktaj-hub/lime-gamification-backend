import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.auth_router import router
from app.auth.dependencies import get_current_user
from app.database import get_db


async def _override_db():
    yield object()


async def _override_user_ok():
    return SimpleNamespace(id=uuid4(), role='student')


async def _override_user_unauthorized():
    raise HTTPException(status_code=401, detail='Could not validate credentials')


class AuthRouterPasswordTests(unittest.TestCase):
    def _make_client(self, user_override=_override_user_ok):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _override_db
        app.dependency_overrides[get_current_user] = user_override
        return TestClient(app)

    def test_change_password_success(self):
        client = self._make_client()
        with patch('app.api.auth_router.AuthService.change_password', new=AsyncMock(return_value=True)):
            response = client.post('/auth/change-password', json={'new_password': 'Password123'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'message': 'Password updated successfully'})

    def test_change_password_unauthorized(self):
        client = self._make_client(user_override=_override_user_unauthorized)
        response = client.post('/auth/change-password', json={'new_password': 'Password123'})

        self.assertEqual(response.status_code, 401)

    def test_change_password_validation(self):
        client = self._make_client()
        response = client.post('/auth/change-password', json={'new_password': 'short'})

        self.assertEqual(response.status_code, 422)

    def test_reset_password_generic_success(self):
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = _override_db
        client = TestClient(app)

        with patch('app.api.auth_router.AuthService.request_password_reset', new=AsyncMock(return_value=None)):
            existing = client.post('/auth/reset-password', json={'email': 'student@example.com'})
            missing = client.post('/auth/reset-password', json={'email': 'missing@example.com'})

        self.assertEqual(existing.status_code, 200)
        self.assertEqual(missing.status_code, 200)
        self.assertEqual(existing.json(), {'message': 'If an account exists, reset instructions were sent.'})
        self.assertEqual(missing.json(), {'message': 'If an account exists, reset instructions were sent.'})


if __name__ == '__main__':
    unittest.main()
