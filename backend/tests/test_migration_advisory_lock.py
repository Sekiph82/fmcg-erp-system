"""Contract tests for Alembic env.py PostgreSQL advisory lock implementation.

No real database connection required — tests inspect source text only.
"""
from __future__ import annotations

import pathlib

import pytest

_ENV_PATH = pathlib.Path(__file__).parent.parent / "alembic" / "env.py"


@pytest.fixture(scope="module")
def env_source() -> str:
    return _ENV_PATH.read_text(encoding="utf-8")


def _fn_body(source: str, fn_name: str) -> str:
    """Return approximate function body lines up to the next top-level definition."""
    lines = source.splitlines()
    in_fn = False
    body: list[str] = []
    for line in lines:
        if line.startswith(f"def {fn_name}(") or line.startswith(f"async def {fn_name}("):
            in_fn = True
        elif in_fn and (
            line.startswith("def ")
            or line.startswith("async def ")
            or line.startswith("class ")
        ):
            break
        if in_fn:
            body.append(line)
    return "\n".join(body)


class TestLockConstant:
    def test_constant_defined(self, env_source):
        assert "MIGRATION_ADVISORY_LOCK_KEY = 20260517" in env_source

    def test_constant_value_in_source(self, env_source):
        assert "20260517" in env_source


class TestLockPresence:
    def test_pg_advisory_lock_in_source(self, env_source):
        assert "pg_advisory_lock" in env_source

    def test_pg_advisory_unlock_in_source(self, env_source):
        assert "pg_advisory_unlock" in env_source

    def test_lock_uses_parameterised_query(self, env_source):
        # Must not build SQL via f-string/concatenation
        assert 'sa.text("SELECT pg_advisory_lock' in env_source or \
               "sa.text('SELECT pg_advisory_lock" in env_source

    def test_unlock_uses_parameterised_query(self, env_source):
        assert 'sa.text("SELECT pg_advisory_unlock' in env_source or \
               "sa.text('SELECT pg_advisory_unlock" in env_source


class TestLockScope:
    def test_lock_inside_do_run_migrations(self, env_source):
        body = _fn_body(env_source, "do_run_migrations")
        assert "pg_advisory_lock" in body

    def test_unlock_inside_do_run_migrations(self, env_source):
        body = _fn_body(env_source, "do_run_migrations")
        assert "pg_advisory_unlock" in body

    def test_offline_migration_does_not_use_lock(self, env_source):
        body = _fn_body(env_source, "run_migrations_offline")
        assert "pg_advisory_lock" not in body

    def test_postgresql_dialect_check_present(self, env_source):
        body = _fn_body(env_source, "do_run_migrations")
        assert "postgresql" in body

    def test_dialect_name_check_present(self, env_source):
        body = _fn_body(env_source, "do_run_migrations")
        assert "dialect.name" in body

    def test_unlock_in_finally_block(self, env_source):
        body = _fn_body(env_source, "do_run_migrations")
        lines = body.splitlines()
        finally_seen = False
        for line in lines:
            if "finally:" in line:
                finally_seen = True
            if finally_seen and "pg_advisory_unlock" in line:
                return  # pass
        pytest.fail("pg_advisory_unlock must be inside the finally block")

    def test_lock_acquired_before_migration_run(self, env_source):
        body = _fn_body(env_source, "do_run_migrations")
        lock_pos = body.find("pg_advisory_lock(")
        run_pos = body.find("context.run_migrations()")
        assert lock_pos < run_pos, "advisory lock must be acquired before context.run_migrations()"
