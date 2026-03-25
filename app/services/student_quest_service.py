from uuid import UUID

import asyncpg
from fastapi import HTTPException

from app.repositories.student_quest_repository import StudentQuestRepository
from app.repositories.quest_repository import QuestRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.achievement_repository import AchievementRepository
from app.dtos.question_dtos import AnswerResponse
from app.dtos.student_quest_dtos import QuestCompleteResponse


class StudentQuestService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.sq_repo = StudentQuestRepository(conn)
        self.quest_repo = QuestRepository(conn)
        self.question_repo = QuestionRepository(conn)
        self.user_repo = UserRepository(conn)
        self.achievement_repo = AchievementRepository(conn)

    async def start_quest(self, student_id: UUID, quest_id: UUID):
        quest = await self.quest_repo.find_active_for_student(quest_id, student_id)
        if not quest or not quest.is_active:
            raise HTTPException(status_code=404, detail="Quest not found or inactive")
        existing = await self.sq_repo.find_any(student_id, quest_id)
        if existing:
            raise HTTPException(status_code=409, detail="Quest already started")
        total = await self.quest_repo.get_question_count(quest_id)
        if total == 0:
            raise HTTPException(status_code=400, detail="Quest has no questions")
        return await self.sq_repo.create(student_id, quest_id, total)

    async def answer_question(
        self, student_id: UUID, quest_id: UUID, answer: str
    ) -> AnswerResponse:
        sq = await self.sq_repo.find_active(student_id, quest_id)
        if not sq:
            raise HTTPException(status_code=404,
                                detail="No active quest. Start the quest first.")

        questions = await self.question_repo.list_by_quest(quest_id)
        if sq.current_q >= len(questions):
            raise HTTPException(status_code=400, detail="All questions already answered")

        current_question = questions[sq.current_q]
        is_correct = answer.upper() == current_question.correct.upper()
        is_last = (sq.current_q + 1) >= sq.total_count

        sq = await self.sq_repo.advance(sq.id, is_correct)

        if is_last:
            await self._complete_quest(student_id, sq.id, quest_id)

        return AnswerResponse(
            correct=is_correct,
            correct_answer=current_question.correct,
            is_last_question=is_last,
            current_q=sq.current_q,
            correct_count=sq.correct_count,
            total_count=sq.total_count,
        )

    async def _complete_quest(
        self, student_id: UUID, sq_id: UUID, quest_id: UUID
    ) -> QuestCompleteResponse:
        await self.sq_repo.complete(sq_id)
        quest = await self.quest_repo.find_by_id(quest_id)
        sd = await self.user_repo.update_student_xp(student_id, quest.xp_reward)

        achievement_name = None
        achievement = await self.achievement_repo.find_by_quest(quest_id)
        if achievement:
            if not await self.achievement_repo.has_achievement(student_id, achievement.id):
                await self.achievement_repo.award(student_id, achievement.id)
                achievement_name = achievement.name

        return QuestCompleteResponse(
            xp_earned=quest.xp_reward, total_xp=sd.total_xp,
            level=sd.level, achievement_earned=achievement_name,
        )

    async def finish_quest(
        self, student_id: UUID, quest_id: UUID
    ) -> QuestCompleteResponse:
        # хз что такое — можно вызвать явно, но последний ответ и так автозавершает
        sq = await self.sq_repo.find_active(student_id, quest_id)
        if sq:
            return await self._complete_quest(student_id, sq.id, quest_id)
        quest = await self.quest_repo.find_by_id(quest_id)
        sd = await self.user_repo.get_student_data(student_id)
        return QuestCompleteResponse(
            xp_earned=0, total_xp=sd.total_xp if sd else 0,
            level=sd.level if sd else 1, achievement_earned=None,
        )
