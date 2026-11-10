import pytest


@pytest.fixture(autouse=True)
def _login_limiter_in_memory(monkeypatch):
    """Keep the login limiter on its in-memory store during tests.

    Without REDIS_URL it defaults to localhost:6379; when a local Redis happens to run
    (e.g. the docker-compose dev stack), failure counters persisted there leak between
    tests that only reset the in-memory state.
    """
    from app.core import login_limiter

    monkeypatch.setattr(login_limiter, "_get_redis", lambda: None)
