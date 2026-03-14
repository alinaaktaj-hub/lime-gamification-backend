#!/usr/bin/env python3
import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import asyncpg
from dotenv import load_dotenv

DEFAULT_PASSWORD = "password123"


@dataclass(frozen=True)
class TeacherSeed:
    username: str
    email: str
    name: str
    surname: str
    group_name: str


@dataclass(frozen=True)
class StudentSeed:
    username: str
    name: str
    surname: str
    teacher_username: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed test teachers/students into the database."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned inserts without writing to the database.",
    )
    return parser.parse_args()


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


REPO_ROOT = get_repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.auth.security import hash_password


def load_database_url() -> str:
    dotenv_path = REPO_ROOT / ".env"
    load_dotenv(dotenv_path=dotenv_path)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            f"DATABASE_URL is missing. Set it in {dotenv_path}"
        )
    return database_url


def build_teacher_seeds() -> list[TeacherSeed]:
    return [
        TeacherSeed(
            username="teacher1",
            email="teacher1@school.com",
            name="Teacher1",
            surname="Test",
            group_name="seed-teacher1-group",
        ),
        TeacherSeed(
            username="teacher2",
            email="teacher2@school.com",
            name="Teacher2",
            surname="Test",
            group_name="seed-teacher2-group",
        ),
        TeacherSeed(
            username="teacher3",
            email="teacher3@school.com",
            name="Teacher3",
            surname="Test",
            group_name="seed-teacher3-group",
        ),
    ]


def build_student_seeds() -> list[StudentSeed]:
    seeds: list[StudentSeed] = []
    for i in range(1, 16):
        teacher_index = ((i - 1) // 5) + 1
        seeds.append(
            StudentSeed(
                username=f"student{i:02d}",
                name=f"Student{i:02d}",
                surname="Test",
                teacher_username=f"teacher{teacher_index}",
            )
        )
    return seeds


async def assert_schema_ready(conn: asyncpg.Connection) -> None:
    table_exists = await conn.fetchval("SELECT to_regclass('public.users') IS NOT NULL")
    if not table_exists:
        raise RuntimeError(
            "Table 'users' does not exist. Start the backend once so init_db can create schema."
        )

    rows = await conn.fetch(
        """SELECT column_name
           FROM information_schema.columns
           WHERE table_schema='public'
             AND table_name='users'
             AND column_name = ANY($1::text[])""",
        ["email", "must_change_password"],
    )
    existing_columns = {row["column_name"] for row in rows}
    required_columns = {"email", "must_change_password"}
    missing = required_columns - existing_columns
    if missing:
        raise RuntimeError(
            "users table is missing required columns: "
            + ", ".join(sorted(missing))
            + ". Start the backend once to apply init_db compatibility migrations."
        )


async def find_user_by_username(
    conn: asyncpg.Connection, username: str
) -> Optional[asyncpg.Record]:
    return await conn.fetchrow(
        "SELECT id, username, role FROM users WHERE username = $1",
        username,
    )


async def ensure_teacher(
    conn: asyncpg.Connection,
    teacher: TeacherSeed,
    dry_run: bool,
) -> tuple[Optional[str], str]:
    existing = await find_user_by_username(conn, teacher.username)
    if existing:
        return str(existing["id"]), "would_skip" if dry_run else "skipped"

    if dry_run:
        return None, "would_create"

    row = await conn.fetchrow(
        """INSERT INTO users (
               name, surname, username, email, hashed_password, role, must_change_password
           )
           VALUES ($1, $2, $3, $4, $5, 'teacher', FALSE)
           RETURNING id""",
        teacher.name,
        teacher.surname,
        teacher.username,
        teacher.email,
        hash_password(DEFAULT_PASSWORD),
    )
    return str(row["id"]), "created"


async def ensure_student(
    conn: asyncpg.Connection,
    student: StudentSeed,
    dry_run: bool,
) -> tuple[Optional[str], str]:
    existing = await find_user_by_username(conn, student.username)
    if existing:
        student_id = str(existing["id"])
        if not dry_run:
            await conn.execute(
                "INSERT INTO student_data (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
                student_id,
            )
        return student_id, "would_skip" if dry_run else "skipped"

    if dry_run:
        return None, "would_create"

    row = await conn.fetchrow(
        """INSERT INTO users (
               name, surname, username, email, hashed_password, role, must_change_password
           )
           VALUES ($1, $2, $3, NULL, $4, 'student', FALSE)
           RETURNING id""",
        student.name,
        student.surname,
        student.username,
        hash_password(DEFAULT_PASSWORD),
    )
    student_id = str(row["id"])
    await conn.execute(
        "INSERT INTO student_data (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
        student_id,
    )
    return student_id, "created"


async def ensure_group(
    conn: asyncpg.Connection,
    teacher_id: Optional[str],
    group_name: str,
    dry_run: bool,
) -> tuple[Optional[str], str]:
    if teacher_id is None:
        return None, "would_create"

    existing = await conn.fetchrow(
        "SELECT id FROM groups WHERE teacher_id = $1 AND name = $2",
        teacher_id,
        group_name,
    )
    if existing:
        return str(existing["id"]), "skipped"

    if dry_run:
        return None, "would_create"

    row = await conn.fetchrow(
        "INSERT INTO groups (name, teacher_id) VALUES ($1, $2) RETURNING id",
        group_name,
        teacher_id,
    )
    return str(row["id"]), "created"


async def ensure_group_membership(
    conn: asyncpg.Connection,
    group_id: Optional[str],
    student_id: Optional[str],
    dry_run: bool,
) -> str:
    if group_id is None or student_id is None:
        return "would_create"

    exists = await conn.fetchval(
        """SELECT EXISTS(
               SELECT 1
               FROM group_students
               WHERE group_id = $1 AND student_id = $2
           )""",
        group_id,
        student_id,
    )
    if exists:
        return "skipped" if not dry_run else "would_skip"

    if dry_run:
        return "would_create"

    await conn.execute(
        """INSERT INTO group_students (group_id, student_id)
           VALUES ($1, $2) ON CONFLICT DO NOTHING""",
        group_id,
        student_id,
    )
    return "created"


def print_summary(
    dry_run: bool,
    teacher_statuses: dict[str, str],
    student_statuses: dict[str, str],
) -> None:
    create_key = "would_create" if dry_run else "created"
    skip_key = "would_skip" if dry_run else "skipped"

    teacher_created = sum(1 for s in teacher_statuses.values() if s == create_key)
    teacher_skipped = sum(1 for s in teacher_statuses.values() if s == skip_key)
    student_created = sum(1 for s in student_statuses.values() if s == create_key)
    student_skipped = sum(1 for s in student_statuses.values() if s == skip_key)

    prefix = "would be " if dry_run else ""
    print("\n=== Summary ===")
    print(f"Teachers: {prefix}created={teacher_created}, {prefix}skipped={teacher_skipped}")
    print(f"Students: {prefix}created={student_created}, {prefix}skipped={student_skipped}")


def print_credentials(
    teachers: list[TeacherSeed],
    students: list[StudentSeed],
    teacher_statuses: dict[str, str],
    student_statuses: dict[str, str],
) -> None:
    print("\n=== Credentials ===")
    print("Teachers:")
    for teacher in teachers:
        status = teacher_statuses[teacher.username]
        print(
            f" - {teacher.username} | email={teacher.email} | password={DEFAULT_PASSWORD} | status={status}"
        )

    print("Students:")
    for student in students:
        status = student_statuses[student.username]
        print(
            f" - {student.username} | password={DEFAULT_PASSWORD} | teacher={student.teacher_username} | status={status}"
        )

    if any(status == "skipped" for status in teacher_statuses.values()) or any(
        status == "skipped" for status in student_statuses.values()
    ):
        print(
            "\nNote: skipped users already existed, so their current password may not be password123."
        )


async def seed_users(dry_run: bool) -> None:
    database_url = load_database_url()
    conn = await asyncpg.connect(database_url)

    try:
        await assert_schema_ready(conn)

        teachers = build_teacher_seeds()
        students = build_student_seeds()

        teacher_ids: dict[str, Optional[str]] = {}
        teacher_statuses: dict[str, str] = {}
        student_ids: dict[str, Optional[str]] = {}
        student_statuses: dict[str, str] = {}

        for teacher in teachers:
            teacher_id, status = await ensure_teacher(conn, teacher, dry_run)
            teacher_ids[teacher.username] = teacher_id
            teacher_statuses[teacher.username] = status

        for student in students:
            student_id, status = await ensure_student(conn, student, dry_run)
            student_ids[student.username] = student_id
            student_statuses[student.username] = status

        print("\n=== Teacher Group Assignment (5 students each) ===")
        for teacher in teachers:
            teacher_id = teacher_ids[teacher.username]
            group_id, group_status = await ensure_group(
                conn,
                teacher_id=teacher_id,
                group_name=teacher.group_name,
                dry_run=dry_run,
            )
            print(
                f"{teacher.username}: group={teacher.group_name} ({group_status})"
            )

            assigned_students = [
                student
                for student in students
                if student.teacher_username == teacher.username
            ]
            for student in assigned_students:
                membership_status = await ensure_group_membership(
                    conn,
                    group_id=group_id,
                    student_id=student_ids[student.username],
                    dry_run=dry_run,
                )
                print(f"  - {student.username}: {membership_status}")

        print_summary(
            dry_run=dry_run,
            teacher_statuses=teacher_statuses,
            student_statuses=student_statuses,
        )
        print_credentials(
            teachers=teachers,
            students=students,
            teacher_statuses=teacher_statuses,
            student_statuses=student_statuses,
        )
    finally:
        await conn.close()


def main() -> None:
    args = parse_args()
    mode = "DRY RUN" if args.dry_run else "LIVE RUN"
    print(f"Starting seed_users.py ({mode})")
    asyncio.run(seed_users(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
