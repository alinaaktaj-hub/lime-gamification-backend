import pytest
from pydantic import ValidationError

from app.dtos.question_dtos import QuestionCreate
from app.dtos.quest_dtos import QuestCreate, QuestUpdate
from app.dtos.user_dtos import StudentCreate


def test_student_create_does_not_require_role():
    student = StudentCreate(
        name="Ada",
        surname="Lovelace",
        username="ada",
        password="secret",
    )

    assert student.username == "ada"


def test_student_create_rejects_role_field():
    with pytest.raises(ValidationError):
        StudentCreate(
            name="Ada",
            surname="Lovelace",
            username="ada",
            password="secret",
            role="student",
        )


def test_quest_create_requires_positive_xp_reward():
    with pytest.raises(ValidationError):
        QuestCreate(title="Quest", xp_reward=0)


def test_quest_update_requires_positive_xp_reward():
    with pytest.raises(ValidationError):
        QuestUpdate(xp_reward=-1)


def test_quest_create_accepts_adaptive_delivery_mode():
    quest = QuestCreate(title="Quest", delivery_mode="adaptive")

    assert quest.delivery_mode == "adaptive"


def test_quest_dtos_reject_invalid_delivery_mode():
    with pytest.raises(ValidationError):
        QuestCreate(title="Quest", delivery_mode="sideways")

    with pytest.raises(ValidationError):
        QuestUpdate(delivery_mode="sideways")


def test_question_create_rejects_invalid_correct_value():
    with pytest.raises(ValidationError):
        QuestionCreate(
            text="Q",
            option_a="A",
            option_b="B",
            correct="Z",
        )


def test_question_create_requires_matching_option_for_c_and_d():
    with pytest.raises(ValidationError):
        QuestionCreate(
            text="Q",
            option_a="A",
            option_b="B",
            correct="C",
        )

    with pytest.raises(ValidationError):
        QuestionCreate(
            text="Q",
            option_a="A",
            option_b="B",
            option_c="C",
            correct="D",
        )


def test_question_create_accepts_difficulty_metadata():
    question = QuestionCreate(
        text="Q",
        option_a="A",
        option_b="B",
        correct="A",
        difficulty_level="hard",
        difficulty_score=0.91,
        difficulty_confidence=0.88,
        difficulty_needs_review=False,
    )

    assert question.difficulty_level == "hard"
    assert question.difficulty_score == 0.91
    assert question.difficulty_confidence == 0.88
    assert question.difficulty_needs_review is False


def test_question_create_rejects_invalid_difficulty_metadata():
    with pytest.raises(ValidationError):
        QuestionCreate(
            text="Q",
            option_a="A",
            option_b="B",
            correct="A",
            difficulty_level="expert",
        )

    with pytest.raises(ValidationError):
        QuestionCreate(
            text="Q",
            option_a="A",
            option_b="B",
            correct="A",
            difficulty_confidence=1.5,
        )
