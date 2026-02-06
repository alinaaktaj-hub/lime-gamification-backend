from typing import List

import asyncpg
from fastapi import APIRouter, Depends

from app.database import get_db
from app.services.leaderboard_service import LeaderboardService
from app.dtos.user_dtos import StudentResponse

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/leaderboard", response_model=List[StudentResponse])
async def public_leaderboard(conn: asyncpg.Connection = Depends(get_db)):
    return await LeaderboardService(conn).get_leaderboard(limit=10)