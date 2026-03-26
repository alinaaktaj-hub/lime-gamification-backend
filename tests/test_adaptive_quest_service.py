from types import SimpleNamespace
from uuid import uuid4

from app.services.adaptive_quest_service import AdaptiveQuestService


def _question(level=None, needs_review=False):
    return SimpleNamespace(
        id=uuid4(),
        difficulty_level=level,
        difficulty_needs_review=needs_review,
    )


def test_select_initial_question_starts_at_medium():
    service = AdaptiveQuestService()
    medium = _question("medium")
    hard = _question("hard")

    decision = service.select_next_question(
        questions=[hard, medium],
        answered_question_ids=set(),
        current_difficulty_level="medium",
        recent_results=[],
        is_initial=True,
    )

    assert decision.question.id == medium.id
    assert decision.target_difficulty_level == "medium"
    assert decision.served_difficulty_level == "medium"
    assert decision.adaptation_action == "start"


def test_two_consecutive_correct_answers_raise_difficulty():
    service = AdaptiveQuestService()
    hard = _question("hard")

    decision = service.select_next_question(
        questions=[hard],
        answered_question_ids=set(),
        current_difficulty_level="medium",
        recent_results=[True, True],
    )

    assert decision.question.id == hard.id
    assert decision.target_difficulty_level == "hard"
    assert decision.served_difficulty_level == "hard"
    assert decision.adaptation_action == "increase"


def test_two_consecutive_incorrect_answers_lower_difficulty():
    service = AdaptiveQuestService()
    easy = _question("easy")

    decision = service.select_next_question(
        questions=[easy],
        answered_question_ids=set(),
        current_difficulty_level="medium",
        recent_results=[False, False],
    )

    assert decision.question.id == easy.id
    assert decision.target_difficulty_level == "easy"
    assert decision.served_difficulty_level == "easy"
    assert decision.adaptation_action == "decrease"


def test_mixed_recent_answers_keep_same_difficulty():
    service = AdaptiveQuestService()
    medium = _question("medium")

    decision = service.select_next_question(
        questions=[medium],
        answered_question_ids=set(),
        current_difficulty_level="medium",
        recent_results=[True, False],
    )

    assert decision.question.id == medium.id
    assert decision.target_difficulty_level == "medium"
    assert decision.served_difficulty_level == "medium"
    assert decision.adaptation_action == "stay"


def test_selection_never_repeats_answered_questions_and_falls_back():
    service = AdaptiveQuestService()
    answered_medium = _question("medium")
    available_easy = _question("easy")

    decision = service.select_next_question(
        questions=[answered_medium, available_easy],
        answered_question_ids={answered_medium.id},
        current_difficulty_level="medium",
        recent_results=[True, False],
    )

    assert decision.question.id == available_easy.id
    assert decision.target_difficulty_level == "medium"
    assert decision.served_difficulty_level == "easy"
    assert "no unanswered medium questions" in decision.adaptation_reason.lower()


def test_unscored_or_review_questions_default_to_medium():
    service = AdaptiveQuestService()
    unscored = _question(level=None, needs_review=True)

    decision = service.select_next_question(
        questions=[unscored],
        answered_question_ids=set(),
        current_difficulty_level="medium",
        recent_results=[],
        is_initial=True,
    )

    assert decision.question.id == unscored.id
    assert decision.served_difficulty_level == "medium"
