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
