from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from fastapi import FastAPI, HTTPException

from app.config import DATABASE_URL, INITIAL_ADMIN_USERNAME, INITIAL_ADMIN_PASSWORD

db_pool: Optional[asyncpg.Pool] = None


async def init_db():
    global db_pool
    db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)

    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name            TEXT NOT NULL,
                surname         TEXT NOT NULL,
                username        TEXT UNIQUE NOT NULL,
                hashed_password TEXT NOT NULL,
                role            TEXT NOT NULL CHECK (role IN ('student','teacher','admin')),
                created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS student_data (
                user_id  UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
                total_xp INTEGER NOT NULL DEFAULT 0,
                level    INTEGER NOT NULL DEFAULT 1
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS quests (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                title       TEXT NOT NULL,
                description TEXT,
                xp_reward   INTEGER NOT NULL DEFAULT 10,
                teacher_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                is_active   BOOLEAN NOT NULL DEFAULT true,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                quest_id   UUID NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
                text       TEXT NOT NULL,
                option_a   TEXT NOT NULL,
                option_b   TEXT NOT NULL,
                option_c   TEXT,
                option_d   TEXT,
                correct    TEXT NOT NULL CHECK (correct IN ('A','B','C','D')),
                sort_order INTEGER NOT NULL DEFAULT 0
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS student_quests (
                id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                student_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                quest_id      UUID NOT NULL REFERENCES quests(id) ON DELETE CASCADE,
                current_q     INTEGER NOT NULL DEFAULT 0,
                correct_count INTEGER NOT NULL DEFAULT 0,
                total_count   INTEGER NOT NULL DEFAULT 0,
                status        TEXT NOT NULL DEFAULT 'in_progress'
                                  CHECK (status IN ('in_progress','completed')),
                started_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                finished_at   TIMESTAMPTZ,
                UNIQUE(student_id, quest_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS groups (
                id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name       TEXT NOT NULL,
                teacher_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS group_students (
                group_id   UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
                student_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                PRIMARY KEY (group_id, student_id)
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS achievements (
                id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                name        TEXT NOT NULL,
                description TEXT,
                quest_id    UUID REFERENCES quests(id) ON DELETE SET NULL,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
        """)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS student_achievements (
                student_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                achievement_id UUID NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
                earned_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (student_id, achievement_id)
            )
        """)

        # это надо удалить крч перед продом
        if INITIAL_ADMIN_USERNAME and INITIAL_ADMIN_PASSWORD:
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM users WHERE username = $1)",
                INITIAL_ADMIN_USERNAME,
            )
            if not exists:
                from app.auth.security import hash_password
                await conn.execute(
                    """INSERT INTO users (name, surname, username, hashed_password, role)
                       VALUES ($1, $2, $3, $4, 'admin')""",
                    "Admin", "Admin", INITIAL_ADMIN_USERNAME,
                    hash_password(INITIAL_ADMIN_PASSWORD),
                )


async def close_db():
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


async def get_db():
    if db_pool is None:
        raise HTTPException(status_code=503, detail="Database not available")
    async with db_pool.acquire() as conn:
        yield conn