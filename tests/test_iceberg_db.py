import asyncio
from pathlib import Path


def test_init_db_adds_group_timezone_and_iceberg_tables(monkeypatch):
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

    async def fake_create_pool(*args, **kwargs):
        return FakePool(FakeConn())

    monkeypatch.setattr(connection, "INITIAL_ADMIN_USERNAME", None)
    monkeypatch.setattr(connection, "INITIAL_ADMIN_PASSWORD", None)
    monkeypatch.setattr(connection.asyncpg, "create_pool", fake_create_pool)

    asyncio.run(connection.init_db())

    normalized = [" ".join(sql.split()) for sql in executed_sql]

    assert any(
        "ALTER TABLE groups ADD COLUMN IF NOT EXISTS timezone TEXT" in sql
        for sql in normalized
    )
    assert any(
        "CREATE TABLE IF NOT EXISTS student_answer_events" in sql
        for sql in normalized
    )
    assert any(
        "CREATE TABLE IF NOT EXISTS iceberg_view_audit" in sql
        for sql in normalized
    )


def test_alembic_migration_exists_for_iceberg_schema():
    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"
    migration_files = sorted(versions_dir.glob("*_iceberg_schema.py"))

    assert migration_files, "Expected an Alembic iceberg schema migration file"

    contents = migration_files[0].read_text(encoding="utf-8")

    assert "student_answer_events" in contents
    assert "iceberg_view_audit" in contents
    assert "timezone" in contents
