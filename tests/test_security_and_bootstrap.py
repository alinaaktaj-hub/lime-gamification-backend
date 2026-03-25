import asyncio
import os
import subprocess
import sys


def test_settings_require_secret_key():
    env = os.environ.copy()
    env["SECRET_KEY"] = ""

    result = subprocess.run(
        [sys.executable, "-c", "import app.config.settings"],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "SECRET_KEY" in (result.stderr + result.stdout)


def test_settings_default_openai_model():
    env = os.environ.copy()
    env["SECRET_KEY"] = "test-secret-key"
    env.pop("OPENAI_MODEL", None)

    result = subprocess.run(
        [sys.executable, "-c", "from app.config.settings import OPENAI_MODEL; print(OPENAI_MODEL)"],
        cwd=os.getcwd(),
        env=env,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "gpt-5.4-nano"


def test_init_db_enables_pgcrypto_before_table_creation(monkeypatch):
    from app.database import connection

    executed_sql = []

    class FakeConn:
        async def execute(self, sql, *args):
            executed_sql.append(sql)
            return "OK"

        async def fetchval(self, sql, *args):
            return False

    class AcquireCtx:
        def __init__(self, conn):
            self._conn = conn

        async def __aenter__(self):
            return self._conn

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakePool:
        def __init__(self, conn):
            self._conn = conn

        def acquire(self):
            return AcquireCtx(self._conn)

        async def close(self):
            return None

    fake_conn = FakeConn()
    fake_pool = FakePool(fake_conn)

    async def fake_create_pool(*args, **kwargs):
        return fake_pool

    monkeypatch.setattr(connection, "INITIAL_ADMIN_USERNAME", None)
    monkeypatch.setattr(connection, "INITIAL_ADMIN_PASSWORD", None)
    monkeypatch.setattr(connection.asyncpg, "create_pool", fake_create_pool)

    asyncio.run(connection.init_db())

    normalized = [" ".join(sql.split()) for sql in executed_sql]
    ext_idx = next(
        i for i, sql in enumerate(normalized)
        if "CREATE EXTENSION IF NOT EXISTS pgcrypto" in sql
    )
    users_idx = next(
        i for i, sql in enumerate(normalized)
        if "CREATE TABLE IF NOT EXISTS users" in sql
    )

    assert ext_idx < users_idx
