# 2FA Implementation Report

Date: 2026-05-18  
Status: **IMPLEMENTATION COMPLETE** (Round 8)

---

## 1. Current TOTP Behavior

**Status: Fully working.**

- `POST /auth/2fa/setup?method=totp` — generates TOTP secret, returns QR code (base64 PNG) + manual key.
- `POST /auth/2fa/verify {code}` — verifies TOTP code, enables 2FA, returns recovery codes.
- `POST /auth/2fa/login-verify {session_token, code}` — verifies TOTP during login.
- `POST /auth/2fa/step-up {code, action}` — verifies TOTP for sensitive actions.
- Recovery codes: 10 bcrypt-hashed XXXX-XXXX codes.
- Login flow: credential check → TOTP challenge → full token issued.

---

## 2. Pre-Round-8 SMS Behavior

**Status: Broken.**

- `setup_2fa(method=SMS)` saved `phone_number` to DB, returned empty response, sent no OTP.
- `verify_and_enable_2fa` raised 400 "Use /login-verify for non-TOTP methods" — setup flow unusable.
- `auth.py` login generated OTP via `generate_otp()`, stored it **plaintext** in `TwoFASession.challenge_code`, had `# TODO: dispatch OTP via notification service` — never dispatched.
- Login-verify did **plaintext** comparison `session.challenge_code == body.code` — insecure.

---

## 3. Pre-Round-8 Email Behavior

**Status: Broken.** Same as SMS above (no OTP sent, no enable flow).

---

## 4. Pre-Round-8 Frontend UI State

- SMS and Email method buttons disabled with `cursor-not-allowed` and "(coming soon)" label.
- No phone number input.
- No OTP entry step for SMS/email.

---

## 5. Backend Endpoints (Pre-Round-8)

| Endpoint | Method | SMS/Email Status |
|---|---|---|
| `GET /auth/2fa/settings` | Working | OK |
| `POST /auth/2fa/setup` | Broken | saves phone/email, no OTP sent, no session |
| `POST /auth/2fa/verify` | Broken | raises 400 for non-TOTP |
| `POST /auth/2fa/enable` | Broken | alias of verify, same issue |
| `POST /auth/2fa/disable` | Working | OK |
| `POST /auth/2fa/login-verify` | Insecure | plaintext OTP compare, OTP never dispatched |
| `POST /auth/2fa/resend-otp` | Missing | not implemented |
| `GET /auth/2fa/recovery-codes` | Working | OK |
| `POST /auth/2fa/recovery-codes/regenerate` | Working | OK |
| `POST /auth/2fa/use-recovery-code` | Working | OK |
| `POST /auth/2fa/step-up` | Partial | TOTP only, SMS/email not supported |

---

## 6. DB Fields / Models (Pre-Round-8)

| Model | Field | Issue |
|---|---|---|
| `User2FASettings` | `secret_key String(64)` | TOTP only |
| `User2FASettings` | `phone_number String(20)` | saved, never used for delivery |
| `User2FASettings` | `email String(255)` | saved, never used for delivery |
| `TwoFASession` | `challenge_code String(10)` | too small for hash (60+ chars), stored plaintext |

---

## 7. Security Risks Found (Pre-Round-8)

| Risk | Severity | Fix |
|---|---|---|
| OTP stored plaintext in DB | HIGH | Hash with bcrypt before storing |
| Plaintext OTP comparison | HIGH | Use hash verification |
| OTP never dispatched to user | HIGH | Wire email/SMS senders |
| No resend cooldown | MEDIUM | Track session.created_at, enforce 60s cooldown |
| SMS/email enable flow broken | MEDIUM | Fix setup + verify endpoints |
| challenge_code column too small | LOW | Migrate String(10) → String(255) |

---

## 8. Implementation Plan (Executed in Round 8)

### A. Schema Migration
- New migration `20260518_0001_otp_delivery.py`
- Expand `two_fa_sessions.challenge_code` String(10) → String(255)

### B. Config Additions
- `OTP_EXPIRY_SECONDS`, `OTP_RESEND_COOLDOWN_SECONDS`, `OTP_MAX_ATTEMPTS`
- `OTP_DEV_DELIVERY_MODE` — log OTP to console in dev, blocked in production
- SMTP vars for email delivery
- SMS vars (Twilio-compatible)
- Production guard: `OTP_DEV_DELIVERY_MODE=true` rejected in production

### C. New Services
- `backend/app/services/email_sender.py` — dev=console log, prod=stdlib smtplib
- `backend/app/services/sms_sender.py` — dev=console log, prod=Twilio via httpx

### D. Security Fixes
- `totp.py`: add `hash_otp()` + `verify_otp_hash()` (bcrypt via existing passlib context)
- `totp.py`: add `create_setup_2fa_token()` / `decode_setup_2fa_token()` (JWT type=2fa_setup)
- `auth.py` login: hash OTP before storing, dispatch via sender
- `two_factor.py` login-verify: use `verify_otp_hash()` instead of plaintext compare

### E. Setup Flow Fix
- `setup_2fa(method=email/sms)`: generate OTP → hash → create TwoFASession → dispatch → return `session_token`
- `verify_and_enable_2fa`: accept optional `session_token`; if SMS/email, decode token, verify hash, enable 2FA

### F. New Endpoint
- `POST /auth/2fa/resend-otp {session_token}` — check 60s cooldown, expire old session, create new session + OTP, dispatch, return new `session_token`

### G. Frontend
- Enable SMS/Email buttons (remove disabled/coming-soon)
- Phone number input for SMS
- OTP entry step for SMS/email after setup
- Resend button with 60s countdown timer

---

## 9. Post-Round-8 Status

| Area | Status |
|---|---|
| TOTP | Unchanged, working |
| Email OTP setup | Implemented |
| SMS OTP setup | Implemented |
| OTP hashing | Implemented (bcrypt) |
| OTP dispatch | Implemented (email: smtplib, SMS: Twilio via httpx) |
| Dev delivery mode | Console log, disabled in production |
| Resend cooldown | 60s, enforced via session.created_at |
| Attempt limits | 5 max, existing mechanism |
| Alembic migration | 20260518_0001 added |
| Frontend SMS/email | Enabled, functional |
| Backend tests | Added in test_otp.py |
| Playwright smoke | Unaffected (52/52) |

---

## 10. Remaining Risks / Future Work

| Item | Note |
|---|---|
| Step-up for SMS/email | Not implemented — requires 2-step request+verify flow. TOTP step-up still works. |
| SMS provider beyond Twilio | Pluggable by SMS_PROVIDER var; only Twilio implemented |
| Email HTML template | Plain text only; add HTML template for branding |
| OTP audit log | Dispatch events logged without OTP value |
| Redis-backed OTP store | Could replace DB sessions for high-volume; not needed at current scale |
