from typing import List

import asyncpg

from app.repositories.user_repository import UserRepository
from app.dtos.user_dtos import StudentResponse


class LeaderboardService:
    def __init__(self, conn: asyncpg.Connection):
        self.user_repo = UserRepository(conn)

    async def get_leaderboard(self, limit: int = 10) -> List[StudentResponse]:
        rows = await self.user_repo.get_leaderboard(limit)
        return [StudentResponse(**r) for r in rows]