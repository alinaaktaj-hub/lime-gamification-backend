from uuid import UUID

import asyncpg
from fastapi import HTTPException

from app.services.adaptive_quest_service import AdaptiveQuestService
from app.repositories.student_quest_repository import StudentQuestRepository
from app.repositories.quest_repository import QuestRepository
from app.repositories.question_repository import QuestionRepository
from app.repositories.user_repository import UserRepository
from app.repositories.achievement_repository import AchievementRepository
from app.repositories.answer_event_repository import AnswerEventRepository
from app.dtos.question_dtos import AnswerResponse, QuestionResponse
from app.dtos.student_quest_dtos import QuestCompleteResponse


class StudentQuestService:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn
        self.sq_repo = StudentQuestRepository(conn)
        self.quest_repo = QuestRepository(conn)
        self.question_repo = QuestionRepository(conn)
        self.user_repo = UserRepository(conn)
        self.achievement_repo = AchievementRepository(conn)
        self.answer_event_repo = AnswerEventRepository(conn) if conn is not None else None
        self.adaptive_service = AdaptiveQuestService()

    async def start_quest(self, student_id: UUID, quest_id: UUID):
        quest = await self.quest_repo.find_active_for_student(student_id, quest_id)
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found or inactive")
        existing = await self.sq_repo.find_any(student_id, quest_id)
        if existing:
            raise HTTPException(status_code=409, detail="Quest already started")
        total = await self.quest_repo.get_question_count(quest_id)
        if total == 0:
            raise HTTPException(status_code=400, detail="Quest has no questions")
        sq = await self.sq_repo.create(student_id, quest_id, total)
        if quest.delivery_mode != "adaptive":
            return sq

        questions = await self.question_repo.list_by_quest(quest_id)
        decision = self.adaptive_service.select_next_question(
            questions=questions,
            answered_question_ids=set(),
            current_difficulty_level="medium",
            recent_results=[],
            is_initial=True,
        )
        return await self.sq_repo.set_current_question(
            sq.id,
            decision.question.id,
            decision.served_difficulty_level,
        )

    async def answer_question(
        self, student_id: UUID, quest_id: UUID, answer: str, question_id: UUID | None = None
    ) -> AnswerResponse:
        sq = await self.sq_repo.find_active(student_id, quest_id)
        if not sq:
            raise HTTPException(status_code=404,
                                detail="No active quest. Start the quest first.")
        quest = await self.quest_repo.find_by_id(quest_id)
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")

        if quest.delivery_mode == "adaptive":
            return await self._answer_adaptive_question(sq, quest_id, answer, question_id)

        questions = await self.question_repo.list_by_quest(quest_id)
        if sq.current_q >= len(questions):
            raise HTTPException(status_code=400, detail="All questions already answered")

        current_question = questions[sq.current_q]
        is_correct = answer.upper() == current_question.correct.upper()
        is_last = (sq.current_q + 1) >= sq.total_count
        question_index = sq.current_q

        sq = await self.sq_repo.advance(sq.id, is_correct)

        if self.answer_event_repo is not None:
            await self.answer_event_repo.record(
                student_id=student_id,
                quest_id=quest_id,
                question_id=current_question.id,
                student_quest_id=sq.id,
                question_index=question_index,
                submitted_answer=answer.upper(),
                is_correct=is_correct,
                served_difficulty=None,
                adaptation_action=None,
                adaptation_reason=None,
            )

        if is_last:
            await self._complete_quest(student_id, sq.id, quest_id)

        return AnswerResponse(
            correct=is_correct,
            correct_answer=current_question.correct,
            is_last_question=is_last,
            current_q=sq.current_q,
            correct_count=sq.correct_count,
            total_count=sq.total_count,
            explanation=None,
        )

    async def _answer_adaptive_question(
        self,
        sq,
        quest_id: UUID,
        answer: str,
        question_id: UUID | None,
    ) -> AnswerResponse:
        if sq.current_question_id is None:
            raise HTTPException(status_code=400, detail="No active adaptive question")
        if question_id is None:
            raise HTTPException(status_code=400, detail="question_id is required for adaptive quests")
        if question_id != sq.current_question_id:
            raise HTTPException(status_code=400, detail="Answered question does not match the active adaptive question")

        current_question = await self.question_repo.find_by_id(question_id)
        if not current_question:
            raise HTTPException(status_code=404, detail="Question not found")

        is_correct = answer.upper() == current_question.correct.upper()
        is_last = (sq.current_q + 1) >= sq.total_count
        question_index = sq.current_q

        if is_last:
            updated_sq = await self.sq_repo.advance_adaptive(
                sq.id,
                is_correct,
                None,
                None,
            )
            if self.answer_event_repo is not None:
                await self.answer_event_repo.record(
                    student_id=sq.student_id,
                    quest_id=quest_id,
                    question_id=current_question.id,
                    student_quest_id=sq.id,
                    question_index=question_index,
                    submitted_answer=answer.upper(),
                    is_correct=is_correct,
                    served_difficulty=sq.current_difficulty_level,
                    adaptation_action="complete",
                    adaptation_reason="Quest completed after reaching the fixed question count.",
                )
            await self._complete_quest(sq.student_id, sq.id, quest_id)
            return AnswerResponse(
                correct=is_correct,
                correct_answer=current_question.correct,
                is_last_question=True,
                current_q=updated_sq.current_q,
                correct_count=updated_sq.correct_count,
                total_count=updated_sq.total_count,
                explanation=self._build_answer_explanation(
                    is_correct,
                    "Quest completed after reaching the fixed question count.",
                ),
                next_difficulty_level=None,
                adaptation_action="complete",
                adaptation_reason="Quest completed after reaching the fixed question count.",
                next_question=None,
            )

        history = []
        if self.answer_event_repo is not None:
            history = await self.answer_event_repo.list_by_student_quest(sq.id)
        recent_results = [event["is_correct"] for event in history] + [is_correct]
        answered_question_ids = {event["question_id"] for event in history}
        answered_question_ids.add(current_question.id)
        questions = await self.question_repo.list_by_quest(quest_id)
        decision = self.adaptive_service.select_next_question(
            questions=questions,
            answered_question_ids=answered_question_ids,
            current_difficulty_level=sq.current_difficulty_level or "medium",
            recent_results=recent_results,
        )
        updated_sq = await self.sq_repo.advance_adaptive(
            sq.id,
            is_correct,
            decision.question.id,
            decision.served_difficulty_level,
        )
        if self.answer_event_repo is not None:
            await self.answer_event_repo.record(
                student_id=sq.student_id,
                quest_id=quest_id,
                question_id=current_question.id,
                student_quest_id=sq.id,
                question_index=question_index,
                submitted_answer=answer.upper(),
                is_correct=is_correct,
                served_difficulty=sq.current_difficulty_level,
                adaptation_action=decision.adaptation_action,
                adaptation_reason=decision.adaptation_reason,
            )
        return AnswerResponse(
            correct=is_correct,
            correct_answer=current_question.correct,
            is_last_question=False,
            current_q=updated_sq.current_q,
            correct_count=updated_sq.correct_count,
            total_count=updated_sq.total_count,
            explanation=self._build_answer_explanation(
                is_correct,
                decision.adaptation_reason,
            ),
            next_difficulty_level=decision.served_difficulty_level,
            adaptation_action=decision.adaptation_action,
            adaptation_reason=decision.adaptation_reason,
            next_question=self._to_question_response(decision.question),
        )

    def _to_question_response(self, question) -> QuestionResponse:
        return QuestionResponse(
            id=question.id,
            quest_id=question.quest_id,
            text=question.text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
            sort_order=question.sort_order,
        )

    def _build_answer_explanation(self, is_correct: bool, adaptation_reason: str) -> str:
        prefix = "Correct." if is_correct else "Incorrect."
        return f"{prefix} {adaptation_reason}"

    async def _complete_quest(
        self, student_id: UUID, sq_id: UUID, quest_id: UUID
    ) -> QuestCompleteResponse:
        async with self.conn.transaction():
            completed = await self.sq_repo.complete(sq_id)
            if not completed:
                raise HTTPException(status_code=409, detail="Quest already completed")

            quest = await self.quest_repo.find_by_id(quest_id)
            if not quest:
                raise HTTPException(status_code=404, detail="Quest not found")

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
        sq = await self.sq_repo.find_active(student_id, quest_id)
        if not sq:
            raise HTTPException(status_code=404, detail="No active quest found")
        if sq.current_q < sq.total_count:
            raise HTTPException(
                status_code=400,
                detail="Answer all quest questions before finishing",
            )
        return await self._complete_quest(student_id, sq.id, quest_id)
