"""
OTP / 2FA delivery unit tests.

Run: cd backend && python -m pytest tests/test_otp.py -v
No DB connection required; all tests are unit-level.
"""
import pytest
import time


# ── OTP generation ────────────────────────────────────────────────────────────

from app.core.totp import generate_otp, hash_otp, verify_otp_hash


class TestOTPGeneration:
    def test_otp_is_six_digits(self):
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()

    def test_otp_is_random(self):
        otps = {generate_otp() for _ in range(20)}
        assert len(otps) > 1  # highly unlikely all 20 are identical

    def test_otp_uses_only_digits(self):
        for _ in range(50):
            otp = generate_otp()
            assert all(c in "0123456789" for c in otp)


# ── OTP hashing ───────────────────────────────────────────────────────────────

class TestOTPHashing:
    def test_hash_is_not_plaintext(self):
        otp = "123456"
        hashed = hash_otp(otp)
        assert hashed != otp
        assert len(hashed) > 20  # bcrypt hashes are ~60 chars

    def test_verify_correct_otp(self):
        otp = "654321"
        hashed = hash_otp(otp)
        assert verify_otp_hash(otp, hashed) is True

    def test_verify_wrong_otp_fails(self):
        hashed = hash_otp("111111")
        assert verify_otp_hash("999999", hashed) is False

    def test_same_otp_different_hashes(self):
        # bcrypt salts ensure two hashes of the same OTP differ
        otp = "555555"
        h1 = hash_otp(otp)
        h2 = hash_otp(otp)
        assert h1 != h2
        assert verify_otp_hash(otp, h1)
        assert verify_otp_hash(otp, h2)

    def test_hash_fits_in_255_chars(self):
        hashed = hash_otp("123456")
        assert len(hashed) <= 255


# ── Setup token ───────────────────────────────────────────────────────────────

from app.core.totp import create_setup_2fa_token, decode_setup_2fa_token


class TestSetupToken:
    def test_roundtrip(self):
        token = create_setup_2fa_token("user-123", "session-456")
        payload = decode_setup_2fa_token(token)
        assert payload is not None
        assert payload["uid"] == "user-123"
        assert payload["sid"] == "session-456"
        assert payload["type"] == "2fa_setup"

    def test_login_token_rejected_as_setup(self):
        from app.core.totp import create_pending_2fa_token
        login_token = create_pending_2fa_token("user-123", "session-456")
        result = decode_setup_2fa_token(login_token)
        assert result is None

    def test_setup_token_rejected_as_login(self):
        from app.core.totp import decode_pending_2fa_token
        setup_token = create_setup_2fa_token("user-123", "session-456")
        result = decode_pending_2fa_token(setup_token)
        assert result is None


# ── Email sender dev mode ─────────────────────────────────────────────────────

class TestEmailSenderDevMode:
    @pytest.mark.asyncio
    async def test_dev_mode_does_not_raise(self, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "OTP_DEV_DELIVERY_MODE", True)
        from app.services.email_sender import send_otp_email
        # Should log and return, not raise
        await send_otp_email("test@example.com", "123456")

    @pytest.mark.asyncio
    async def test_prod_mode_raises_without_smtp_host(self, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "OTP_DEV_DELIVERY_MODE", False)
        monkeypatch.setattr(settings, "SMTP_HOST", "")
        from app.services.email_sender import send_otp_email
        with pytest.raises(RuntimeError, match="SMTP_HOST"):
            await send_otp_email("test@example.com", "123456")


# ── SMS sender dev mode ───────────────────────────────────────────────────────

class TestSMSSenderDevMode:
    @pytest.mark.asyncio
    async def test_dev_mode_does_not_raise(self, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "OTP_DEV_DELIVERY_MODE", True)
        from app.services.sms_sender import send_otp_sms
        await send_otp_sms("+254700000000", "654321")

    @pytest.mark.asyncio
    async def test_prod_mode_raises_without_provider(self, monkeypatch):
        from app.core.config import settings
        monkeypatch.setattr(settings, "OTP_DEV_DELIVERY_MODE", False)
        monkeypatch.setattr(settings, "SMS_PROVIDER", "")
        monkeypatch.setattr(settings, "SMS_ACCOUNT_SID", "")
        from app.services.sms_sender import send_otp_sms
        with pytest.raises(RuntimeError):
            await send_otp_sms("+254700000000", "654321")


# ── Production config guard ───────────────────────────────────────────────────

class TestProductionConfigGuard:
    def test_otp_dev_mode_blocked_in_production(self):
        from pydantic import ValidationError
        from app.core.config import Settings
        with pytest.raises((ValidationError, ValueError)):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="a" * 64,
                AUTH_COOKIE_SECURE=True,
                PASSWORD_REQUIRE_SPECIAL=True,
                SEED_DEMO_DATA=False,
                SYNC_INITIAL_ADMIN_PASSWORD=False,
                OTP_DEV_DELIVERY_MODE=True,
                INITIAL_ADMIN_PASSWORD="StrongPass1!",
            )

    def test_missing_smtp_host_blocked_in_production_when_email_otp_enabled(self):
        from pydantic import ValidationError
        from app.core.config import Settings
        with pytest.raises((ValidationError, ValueError), match="SMTP_HOST"):
            Settings(
                ENVIRONMENT="production",
                SECRET_KEY="a" * 64,
                AUTH_COOKIE_SECURE=True,
                PASSWORD_REQUIRE_SPECIAL=True,
                SEED_DEMO_DATA=False,
                SYNC_INITIAL_ADMIN_PASSWORD=False,
                OTP_DEV_DELIVERY_MODE=False,
                INITIAL_ADMIN_PASSWORD="StrongPass1!",
                REDIS_PASSWORD="str0ngR3disP@ss",
                TWO_FACTOR_EMAIL_ENABLED=True,
                SMTP_HOST="",  # empty — should fail
            )
