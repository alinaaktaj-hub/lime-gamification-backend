from dataclasses import dataclass
from typing import Iterable, Optional


DIFFICULTY_ORDER = ("easy", "medium", "hard")


@dataclass
class AdaptiveSelectionDecision:
    question: object
    target_difficulty_level: str
    served_difficulty_level: str
    adaptation_action: str
    adaptation_reason: str


class AdaptiveQuestService:
    def normalize_difficulty(self, question) -> str:
        if getattr(question, "difficulty_needs_review", False):
            return "medium"
        level = getattr(question, "difficulty_level", None)
        if level in DIFFICULTY_ORDER:
            return level
        return "medium"

    def select_next_question(
        self,
        *,
        questions: Iterable[object],
        answered_question_ids: set,
        current_difficulty_level: str,
        recent_results: list[bool],
        is_initial: bool = False,
    ) -> AdaptiveSelectionDecision:
        unanswered = [q for q in questions if getattr(q, "id") not in answered_question_ids]
        if not unanswered:
            raise ValueError("No unanswered questions available for adaptive selection")

        target_level, action, base_reason = self._determine_target_level(
            current_difficulty_level=current_difficulty_level,
            recent_results=recent_results,
            is_initial=is_initial,
        )
        served_level = self._resolve_served_level(target_level, unanswered)
        question = next(
            question for question in unanswered
            if self.normalize_difficulty(question) == served_level
        )
        reason = base_reason
        if served_level != target_level:
            reason = (
                f"{base_reason} Served {served_level} because no unanswered "
                f"{target_level} questions were available."
            )
        return AdaptiveSelectionDecision(
            question=question,
            target_difficulty_level=target_level,
            served_difficulty_level=served_level,
            adaptation_action=action,
            adaptation_reason=reason,
        )

    def _determine_target_level(
        self,
        *,
        current_difficulty_level: str,
        recent_results: list[bool],
        is_initial: bool,
    ) -> tuple[str, str, str]:
        if is_initial:
            return ("medium", "start", "Quest starts at medium difficulty.")
        if recent_results[-2:] == [True, True]:
            return (
                self._shift_difficulty(current_difficulty_level, 1),
                "increase",
                "Difficulty raised after 2 consecutive correct answers.",
            )
        if recent_results[-2:] == [False, False]:
            return (
                self._shift_difficulty(current_difficulty_level, -1),
                "decrease",
                "Difficulty lowered after 2 consecutive incorrect answers.",
            )
        return (
            current_difficulty_level,
            "stay",
            "Difficulty stayed the same because recent answers were mixed.",
        )

    def _resolve_served_level(self, target_level: str, questions: list[object]) -> str:
        available_levels = {self.normalize_difficulty(question) for question in questions}
        target_index = DIFFICULTY_ORDER.index(target_level)
        for candidate_index in sorted(
            range(len(DIFFICULTY_ORDER)),
            key=lambda index: (abs(index - target_index), index),
        ):
            candidate_level = DIFFICULTY_ORDER[candidate_index]
            if candidate_level in available_levels:
                return candidate_level
        raise ValueError("No available difficulty level found")

    def _shift_difficulty(self, current_difficulty_level: str, delta: int) -> str:
        current_index = DIFFICULTY_ORDER.index(current_difficulty_level)
        next_index = max(0, min(len(DIFFICULTY_ORDER) - 1, current_index + delta))
        return DIFFICULTY_ORDER[next_index]
