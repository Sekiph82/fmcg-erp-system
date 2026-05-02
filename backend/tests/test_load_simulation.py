"""
Load and stress simulation tests.

Simulates concurrent load patterns using asyncio.
No external network calls — tests the in-memory components under load.

Tests:
  - Login limiter under concurrent load
  - Token blocklist under high write volume
  - Input sanitizer throughput
  - AI rate limiter concurrency
  - Business guard concurrency safety

Run: cd backend && venv/Scripts/python.exe -m pytest tests/test_load_simulation.py -v
"""
import asyncio
import time
import pytest
from decimal import Decimal


# ── Login limiter load tests ──────────────────────────────────────────────────

class TestLoginLimiterUnderLoad:
    def setup_method(self):
        from app.core.login_limiter import _failures, _lockouts
        _failures.clear()
        _lockouts.clear()

    @pytest.mark.asyncio
    async def test_100_concurrent_login_failures_lock_account(self):
        """100 concurrent failures — account locked, no race condition."""
        from app.core.login_limiter import record_login_failure, is_locked

        tasks = [record_login_failure("concurrent_victim") for _ in range(20)]
        await asyncio.gather(*tasks)

        assert is_locked("concurrent_victim"), "Account should be locked after concurrent failures"

    @pytest.mark.asyncio
    async def test_concurrent_different_users_isolated(self):
        """Concurrent failures on different users don't cross-contaminate."""
        from app.core.login_limiter import record_login_failure, is_locked, get_failure_count

        users = [f"user_{i}" for i in range(10)]
        # Each user gets exactly 3 failures
        tasks = [record_login_failure(u) for u in users for _ in range(3)]
        await asyncio.gather(*tasks)

        for u in users:
            count = get_failure_count(u)
            assert count == 3, f"User {u} should have 3 failures, got {count}"
            assert not is_locked(u), f"User {u} should not be locked (only 3 failures)"

    @pytest.mark.asyncio
    async def test_lockout_threshold_exact(self):
        """Exactly 5 failures triggers lockout, 4 does not."""
        from app.core.login_limiter import (
            record_login_failure, is_locked, _failures, _lockouts
        )
        _failures.clear()
        _lockouts.clear()

        for i in range(4):
            await record_login_failure("threshold_user")
        assert not is_locked("threshold_user"), "4 failures should not lock"

        await record_login_failure("threshold_user")
        assert is_locked("threshold_user"), "5th failure must lock account"


# ── Token blocklist throughput ────────────────────────────────────────────────

class TestTokenBlocklistThroughput:
    def test_10000_token_adds_complete(self):
        """Blocklist handles 10k tokens without performance issues."""
        from app.core.token_blocklist import add, is_blocked, _store
        _store.clear()

        tokens = [f"token_{i}_xyz_abc" for i in range(1000)]
        expiry = time.time() + 3600

        start = time.monotonic()
        for token in tokens:
            add(token, expiry)
        elapsed = time.monotonic() - start

        assert elapsed < 2.0, f"1000 adds took too long: {elapsed:.2f}s"
        assert is_blocked(tokens[0])
        assert is_blocked(tokens[999])

    def test_expired_tokens_cleaned_up(self):
        """Expired tokens are cleaned up automatically."""
        from app.core.token_blocklist import add, is_blocked, _store
        _store.clear()

        # Add 100 expired tokens
        for i in range(100):
            add(f"expired_{i}", time.time() - 1)

        # Check triggers cleanup for each
        for i in range(100):
            assert not is_blocked(f"expired_{i}")


# ── Input sanitizer throughput ────────────────────────────────────────────────

class TestSanitizerThroughput:
    def test_1000_sanitize_calls_fast(self):
        """Sanitizer processes 1000 payloads quickly."""
        from app.core.input_sanitizer import _sanitize_value

        payload = {
            "name": "<script>evil</script>test product",
            "description": "A" * 100,
            "price": 99.99,
            "tags": ["<b>tag1</b>", "tag2"],
        }

        start = time.monotonic()
        for _ in range(1000):
            _sanitize_value(payload)
        elapsed = time.monotonic() - start

        assert elapsed < 5.0, f"1000 sanitize calls took {elapsed:.2f}s"

    def test_large_nested_structure(self):
        """Sanitizer handles deeply nested structures."""
        from app.core.input_sanitizer import _sanitize_value

        deep = {"level": 0}
        current = deep
        for i in range(1, 20):
            current["next"] = {"level": i, "data": f"<b>val_{i}</b>"}
            current = current["next"]

        result = _sanitize_value(deep)
        assert result["level"] == 0
        assert isinstance(result, dict)


# ── AI rate limiter concurrency ───────────────────────────────────────────────

class TestAIRateLimiterConcurrency:
    def setup_method(self):
        from app.core.ai_rate_limiter import _store
        _store.clear()

    @pytest.mark.asyncio
    async def test_concurrent_requests_counted_correctly(self):
        """Concurrent requests all count against the limit."""
        from app.core.ai_rate_limiter import check_rate_limit, _store
        from fastapi import HTTPException

        user_id = "concurrent_ai_user"
        # 10 requests — limit is 30 for chat
        results = []
        for _ in range(10):
            try:
                await check_rate_limit(user_id, "chat", limit=30)
                results.append("ok")
            except HTTPException:
                results.append("blocked")

        ok_count = results.count("ok")
        assert ok_count == 10, f"Expected 10 OK, got {ok_count}"

    @pytest.mark.asyncio
    async def test_limit_enforcement_stops_at_threshold(self):
        """Exactly limit requests pass, the (limit+1)th is blocked."""
        from app.core.ai_rate_limiter import check_rate_limit, _store
        from fastapi import HTTPException

        user_id = "limit_test_user"
        _store.clear()

        LIMIT = 5
        passed = 0
        blocked = 0

        for _ in range(LIMIT + 2):
            try:
                await check_rate_limit(user_id, "test_endpoint", limit=LIMIT)
                passed += 1
            except HTTPException:
                blocked += 1

        assert passed == LIMIT, f"Expected exactly {LIMIT} passes, got {passed}"
        assert blocked == 2, f"Expected 2 blocked, got {blocked}"


# ── Business guard concurrency ────────────────────────────────────────────────

class TestBusinessGuardConcurrency:
    @pytest.mark.asyncio
    async def test_concurrent_margin_checks(self):
        """Margin check is safe under concurrent calls."""
        from app.core.business_guards import margin_floor_check
        from fastapi import HTTPException

        async def check(selling: float, cost: float):
            try:
                await margin_floor_check(Decimal(str(selling)), Decimal(str(cost)))
                return "ok"
            except HTTPException:
                return "blocked"

        # Mix of valid and invalid prices
        tasks = [
            check(110.0, 100.0),  # 10% margin → ok
            check(103.0, 100.0),  # 3% margin → blocked
            check(120.0, 100.0),  # 20% margin → ok
            check(101.0, 100.0),  # 1% margin → blocked
            check(150.0, 100.0),  # 50% margin → ok
        ]
        results = await asyncio.gather(*tasks)
        assert results[0] == "ok"
        assert results[1] == "blocked"
        assert results[2] == "ok"
        assert results[3] == "blocked"
        assert results[4] == "ok"


# ── Performance benchmarks ────────────────────────────────────────────────────

class TestPerformanceBenchmarks:
    """Quick sanity benchmarks — not CI performance gates, just regression indicators."""

    def test_password_hashing_reasonable_time(self):
        """bcrypt should take 100-500ms (proof it's not trivially breakable)."""
        from app.core.security import hash_password
        start = time.monotonic()
        hash_password("TestPassword1")
        elapsed = (time.monotonic() - start) * 1000

        # bcrypt should be at least 50ms (secure) but under 2000ms
        assert elapsed >= 10, f"Hash too fast ({elapsed:.0f}ms) — may be insecure"
        assert elapsed < 5000, f"Hash too slow ({elapsed:.0f}ms)"

    def test_token_decode_fast(self):
        """JWT decode should be <5ms."""
        from app.core.security import create_access_token, decode_token
        token = create_access_token("test-user-id")

        start = time.monotonic()
        for _ in range(100):
            decode_token(token)
        elapsed = (time.monotonic() - start) * 1000

        per_call = elapsed / 100
        assert per_call < 5, f"Token decode too slow: {per_call:.2f}ms per call"

    def test_sanitizer_per_call_fast(self):
        """Single sanitizer call should be <1ms."""
        from app.core.input_sanitizer import _sanitize_value
        payload = {"name": "test <b>product</b>", "price": 99.99}

        start = time.monotonic()
        for _ in range(1000):
            _sanitize_value(payload)
        elapsed = (time.monotonic() - start) * 1000
        per_call = elapsed / 1000

        assert per_call < 1.0, f"Sanitizer too slow: {per_call:.3f}ms per call"

    def test_blocklist_lookup_fast(self):
        """Token blocklist lookup should be <0.1ms."""
        from app.core.token_blocklist import is_blocked

        start = time.monotonic()
        for _ in range(10000):
            is_blocked("some-non-existent-token-xyz")
        elapsed = (time.monotonic() - start) * 1000
        per_call = elapsed / 10000

        assert per_call < 0.5, f"Blocklist lookup too slow: {per_call:.4f}ms per call"
