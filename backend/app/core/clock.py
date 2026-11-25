"""Single source of "now" for provider adapters (M43.S00.T004) so contract tests can pin time deterministically."""
from datetime import datetime, timezone


def utcnow() -> datetime:   # tests: monkeypatch app.core.clock.utcnow
    return datetime.now(timezone.utc)
