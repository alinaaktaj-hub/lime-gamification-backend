from typing import List
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends

from app.database import get_db
from app.auth.dependencies import require_student
from app.entities.user import UserEntity
from app.services.quest_service import QuestService
from app.services.student_quest_service import StudentQuestService
from app.services.leaderboard_service import LeaderboardService
from app.repositories.achievement_repository import AchievementRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.student_quest_repository import StudentQuestRepository
from app.dtos.quest_dtos import QuestResponse
from app.dtos.question_dtos import AnswerRequest, AnswerResponse, QuestionResponse
from app.dtos.student_quest_dtos import StudentQuestResponse, QuestCompleteResponse
from app.dtos.user_dtos import StudentResponse
from app.dtos.achievement_dtos import StudentAchievementResponse

router = APIRouter(prefix="/student", tags=["student"])


@router.get("/quests", response_model=List[QuestResponse])
async def list_quests(
    user: UserEntity = Depends(require_student),
    conn: asyncpg.Connection = Depends(get_db),
):
    return await QuestService(conn).list_visible_quests(user.id)


@router.get("/quests/{quest_id}", response_model=QuestResponse)
async def get_quest(
    quest_id: UUID,
    user: UserEntity = Depends(require_student),
    conn: asyncpg.Connection = Depends(get_db),
):
    return await QuestService(conn).get_visible_quest(user.id, quest_id)


@router.get("/quests/{quest_id}/questions", response_model=List[QuestionResponse])
async def get_quest_questions(
    quest_id: UUID,
    user: UserEntity = Depends(require_student),
    conn: asyncpg.Connection = Depends(get_db),
):
    await QuestService(conn).get_visible_quest(user.id, quest_id)
    entities = await QuestionRepository(conn).list_by_quest(quest_id)
    return [
        QuestionResponse(
            id=q.id, quest_id=q.quest_id, text=q.text,
            option_a=q.option_a, option_b=q.option_b,
            option_c=q.option_c, option_d=q.option_d,
            sort_order=q.sort_order,
        )
        for q in entities
    ]


@router.post("/quests/{quest_id}/start", response_model=StudentQuestResponse)
async def start_quest(
    quest_id: UUID,
    user: UserEntity = Depends(require_student),
    conn: asyncpg.Connection = Depends(get_db),
):
    sq = await StudentQuestService(conn).start_quest(user.id, quest_id)
    return StudentQuestResponse(
        id=sq.id, student_id=sq.student_id, quest_id=sq.quest_id,
        current_q=sq.current_q, correct_count=sq.correct_count,
        total_count=sq.total_count, status=sq.status,
        started_at=sq.started_at, finished_at=sq.finished_at,
    )


@router.post("/quests/answer", response_model=AnswerResponse)
async def answer_question(
    body: AnswerRequest,
    user: UserEntity = Depends(require_student),
    conn: asyncpg.Connection = Depends(get_db),
):
    return await StudentQuestService(conn).answer_question(
        user.id, body.quest_id, body.answer
    )


@router.post("/quests/{quest_id}/finish", response_model=QuestCompleteResponse)
async def finish_quest(
    quest_id: UUID,
    user: UserEntity = Depends(require_student),
    conn: asyncpg.Connection = Depends(get_db),
):
    return await StudentQuestService(conn).finish_quest(user.id, quest_id)


@router.get("/my-quests", response_model=List[StudentQuestResponse])
async def my_quests(
    user: UserEntity = Depends(require_student),
    conn: asyncpg.Connection = Depends(get_db),
):
    rows = await StudentQuestRepository(conn).list_by_student(user.id)
    return [StudentQuestResponse(**r) for r in rows]


@router.get("/achievements", response_model=List[StudentAchievementResponse])
async def my_achievements(
    user: UserEntity = Depends(require_student),
    conn: asyncpg.Connection = Depends(get_db),
):
    rows = await AchievementRepository(conn).list_by_student(user.id)
    return [StudentAchievementResponse(**r) for r in rows]


@router.get("/leaderboard", response_model=List[StudentResponse])
async def leaderboard(
    user: UserEntity = Depends(require_student),
    conn: asyncpg.Connection = Depends(get_db),
):
    return await LeaderboardService(conn).get_leaderboard(limit=5)
