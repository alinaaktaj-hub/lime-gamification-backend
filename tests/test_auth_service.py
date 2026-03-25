import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.services.auth_service import AuthService


class AuthServicePasswordTests(unittest.IsolatedAsyncioTestCase):
    async def test_change_password_hashes_and_persists(self):
        service = AuthService(conn=None)
        service.user_repo = AsyncMock()
        service.user_repo.update_password_hash.return_value = True

        user_id = uuid4()
        with patch('app.services.auth_service.hash_password', return_value='hashed-value') as mock_hash:
            updated = await service.change_password(user_id, 'Password123')

        self.assertTrue(updated)
        mock_hash.assert_called_once_with('Password123')
        service.user_repo.update_password_hash.assert_awaited_once_with(user_id, 'hashed-value')

    async def test_change_password_returns_false_when_user_not_updated(self):
        service = AuthService(conn=None)
        service.user_repo = AsyncMock()
        service.user_repo.update_password_hash.return_value = False

        updated = await service.change_password(uuid4(), 'Password123')

        self.assertFalse(updated)

    async def test_request_password_reset_is_generic_noop(self):
        service = AuthService(conn=None)
        service.user_repo = SimpleNamespace()

        result = await service.request_password_reset('student@example.com')

        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
