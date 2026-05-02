"""
Security unit tests — cover core security controls.

Run: cd backend && python -m pytest tests/test_security.py -v
No DB connection required; all tests are unit-level.
"""
import pytest
import time


# ── Password policy tests ──────────────────────────────────────────────────────

from app.core.password_policy import validate_password, password_meets_policy, PasswordPolicyError


class TestPasswordPolicy:
    def test_valid_password_passes(self):
        validate_password("StrongPass1")  # should not raise

    def test_too_short_fails(self):
        ok, violations = password_meets_policy("Short1")
        assert not ok
        assert any("8 characters" in v for v in violations)

    def test_no_uppercase_fails(self):
        ok, violations = password_meets_policy("weakpass1")
        assert not ok
        assert any("uppercase" in v for v in violations)

    def test_no_lowercase_fails(self):
        ok, violations = password_meets_policy("STRONGPASS1")
        assert not ok
        assert any("lowercase" in v for v in violations)

    def test_no_digit_fails(self):
        ok, violations = password_meets_policy("StrongPass")
        assert not ok
        assert any("digit" in v for v in violations)

    def test_common_password_blocked(self):
        ok, violations = password_meets_policy("admin123")
        assert not ok
        assert any("common" in v.lower() for v in violations)

    def test_same_as_username_blocked(self):
        # password == username (case-insensitive) → blocked
        ok, violations = password_meets_policy("Myusername", username="Myusername")
        assert not ok
        assert any("username" in v.lower() for v in violations)

    def test_password_with_username_plus_digit_allowed(self):
        # "MyUsername1" != "myusername" → allowed (different string)
        ok, _ = password_meets_policy("MyUsername1", username="myusername")
        assert ok

    def test_multiple_violations_reported(self):
        ok, violations = password_meets_policy("weak")
        assert not ok
        assert len(violations) >= 2

    def test_raises_policy_error(self):
        with pytest.raises(PasswordPolicyError) as exc_info:
            validate_password("bad")
        assert exc_info.value.violations


# ── Login limiter tests ────────────────────────────────────────────────────────

from app.core.login_limiter import (
    check_login_allowed, record_login_failure, clear_login_failures,
    get_failure_count, is_locked, _failures, _lockouts,
)


class TestLoginLimiter:
    def setup_method(self):
        """Clear limiter state before each test."""
        _failures.clear()
        _lockouts.clear()

    @pytest.mark.asyncio
    async def test_first_attempt_allowed(self):
        await check_login_allowed("testuser")  # should not raise

    @pytest.mark.asyncio
    async def test_failure_count_increments(self):
        count = await record_login_failure("user_a")
        assert count == 1
        count = await record_login_failure("user_a")
        assert count == 2

    @pytest.mark.asyncio
    async def test_lockout_after_max_attempts(self):
        from fastapi import HTTPException
        for _ in range(5):
            await record_login_failure("baduser")
        assert is_locked("baduser")
        with pytest.raises(HTTPException) as exc:
            await check_login_allowed("baduser")
        assert exc.value.status_code == 429

    @pytest.mark.asyncio
    async def test_clear_resets_failures(self):
        await record_login_failure("resetuser")
        clear_login_failures("resetuser")
        assert get_failure_count("resetuser") == 0
        assert not is_locked("resetuser")


# ── Token blocklist tests ──────────────────────────────────────────────────────

from app.core.token_blocklist import add, is_blocked, store_size


class TestTokenBlocklist:
    def test_fresh_token_not_blocked(self):
        assert not is_blocked("some-fresh-token-abc123")

    def test_added_token_is_blocked(self):
        token = "token-to-block-xyz"
        expiry = time.time() + 3600
        add(token, expiry)
        assert is_blocked(token)

    def test_expired_token_auto_cleared(self):
        token = "expired-token-test"
        add(token, time.time() - 1)  # already expired
        assert not is_blocked(token)

    def test_different_tokens_independent(self):
        add("blocked-one", time.time() + 3600)
        assert not is_blocked("different-token")


# ── Input sanitizer tests ──────────────────────────────────────────────────────

from app.core.input_sanitizer import _sanitize_value


class TestInputSanitizer:
    def test_plain_string_unchanged(self):
        assert _sanitize_value("Hello World") == "Hello World"

    def test_script_tag_stripped(self):
        result = _sanitize_value("<script>alert('xss')</script>harmless")
        assert "<script>" not in result
        assert "harmless" in result

    def test_html_tags_stripped(self):
        result = _sanitize_value("<b>bold</b>")
        assert "<b>" not in result
        assert "bold" in result

    def test_null_bytes_removed(self):
        result = _sanitize_value("clean\x00data")
        assert "\x00" not in result
        assert "cleandata" in result

    def test_nested_dict_sanitized(self):
        data = {"name": "<script>evil</script>", "amount": 100}
        result = _sanitize_value(data)
        assert "<script>" not in result["name"]
        assert result["amount"] == 100

    def test_list_sanitized(self):
        data = ["<script>xss</script>", "safe"]
        result = _sanitize_value(data)
        assert "<script>" not in result[0]
        assert result[1] == "safe"

    def test_non_string_unchanged(self):
        assert _sanitize_value(42) == 42
        assert _sanitize_value(3.14) == 3.14
        assert _sanitize_value(None) is None
        assert _sanitize_value(True) is True

    def test_oversized_string_truncated(self):
        big = "a" * 15_000
        result = _sanitize_value(big)
        assert len(result) == 10_000


# ── Business guard tests ───────────────────────────────────────────────────────

from decimal import Decimal
from app.core.business_guards import (
    margin_floor_check, stock_adjustment_requires_reason,
    expense_approval_required, payroll_statutory_completeness,
    invoice_match_payment_block,
)


class TestBusinessGuards:
    @pytest.mark.asyncio
    async def test_margin_above_floor_ok(self):
        await margin_floor_check(Decimal("120"), Decimal("100"), Decimal("5"))

    @pytest.mark.asyncio
    async def test_margin_below_floor_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await margin_floor_check(Decimal("102"), Decimal("100"), Decimal("5"))
        assert exc.value.status_code == 422

    @pytest.mark.asyncio
    async def test_margin_below_floor_with_approver_ok(self):
        # Should not raise if approver_override=True
        await margin_floor_check(Decimal("102"), Decimal("100"), Decimal("5"), approver_override=True)

    def test_negative_stock_without_reason_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            stock_adjustment_requires_reason(Decimal("-10"), reason=None)

    def test_negative_stock_with_reason_ok(self):
        stock_adjustment_requires_reason(Decimal("-10"), reason="Damaged goods write-off")

    def test_positive_stock_no_reason_ok(self):
        stock_adjustment_requires_reason(Decimal("10"), reason=None)

    def test_expense_above_threshold_not_approved_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            expense_approval_required(Decimal("15000"), threshold=Decimal("10000"))

    def test_expense_above_threshold_approved_ok(self):
        expense_approval_required(Decimal("15000"), threshold=Decimal("10000"), already_approved=True)

    def test_expense_below_threshold_ok(self):
        expense_approval_required(Decimal("5000"), threshold=Decimal("10000"))

    def test_payroll_missing_kra_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            payroll_statutory_completeness(None, "NHIF123", "NSSF456")
        assert "KRA PIN" in str(exc.value.detail)

    def test_payroll_all_fields_ok(self):
        payroll_statutory_completeness("A123456789P", "NHIF123", "NSSF456")

    def test_invoice_match_blocked_status_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            invoice_match_payment_block("INV-001", "UNMATCHED", policy_blocks_payment=True)

    def test_invoice_match_matched_status_ok(self):
        invoice_match_payment_block("INV-001", "MATCHED", policy_blocks_payment=True)


# ── File validator tests ───────────────────────────────────────────────────────

from app.core.file_validator import sanitize_filename


class TestFileValidator:
    def test_safe_filename_unchanged(self):
        assert sanitize_filename("report.pdf") == "report.pdf"

    def test_path_traversal_stripped(self):
        result = sanitize_filename("../../etc/passwd")
        assert ".." not in result
        assert "/" not in result

    def test_special_chars_replaced(self):
        result = sanitize_filename("my file (1).pdf")
        assert " " not in result
        assert "(" not in result

    def test_leading_dots_stripped(self):
        result = sanitize_filename(".hidden")
        assert not result.startswith(".")

    def test_long_name_truncated(self):
        result = sanitize_filename("a" * 300 + ".pdf")
        assert len(result) <= 255


# ── Security headers tests ────────────────────────────────────────────────────

class TestSecurityHeaders:
    """Verify the security headers module defines expected values."""
    def test_module_importable(self):
        from app.core.security_headers import SecurityHeadersMiddleware
        assert SecurityHeadersMiddleware is not None

    def test_no_cache_paths_defined(self):
        from app.core.security_headers import _NO_CACHE_PREFIXES
        assert "/api/v1/auth" in _NO_CACHE_PREFIXES
        assert "/api/v1/ai" in _NO_CACHE_PREFIXES


# ── Exception handler tests ────────────────────────────────────────────────────

from app.core.exception_handlers import _status_label


class TestExceptionHandlers:
    def test_known_status_labels(self):
        assert _status_label(401) == "unauthorized"
        assert _status_label(403) == "forbidden"
        assert _status_label(422) == "unprocessable_entity"
        assert _status_label(429) == "rate_limit_exceeded"
        assert _status_label(500) == "internal_server_error"

    def test_unknown_status_generic(self):
        label = _status_label(418)
        assert "418" in label
