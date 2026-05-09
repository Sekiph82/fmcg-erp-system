"""
Password policy enforcement.

Rules:
  - Minimum 8 characters
  - At least 1 uppercase letter
  - At least 1 lowercase letter
  - At least 1 digit
  - At least 1 special character (optional, controlled by REQUIRE_SPECIAL)
  - Not in common password blocklist
  - Not equal to username (checked where username is available)
"""
from __future__ import annotations

import re

# ── Configuration ──────────────────────────────────────────────────────────────

MIN_LENGTH = 8
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_DIGIT = True
REQUIRE_SPECIAL = False      # default; overridden at runtime by settings.PASSWORD_REQUIRE_SPECIAL

_SPECIAL_CHARS = r"!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?`~"

# Minimal common-password blocklist (expand in production)
_COMMON_PASSWORDS = {
    "password", "password1", "Password1", "12345678", "123456789",
    "qwerty123", "letmein", "welcome1", "admin123", "changeme",
    "iloveyou", "monkey123", "dragon", "master", "abc12345",
    "erp12345", "fmcg2024", "fmcg2025", "Admin1234",
}

# ── Validation ─────────────────────────────────────────────────────────────────

class PasswordPolicyError(ValueError):
    """Raised when a password violates policy."""
    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))


def validate_password(password: str, username: str | None = None) -> None:
    """
    Validate a plaintext password against the policy.
    Raises PasswordPolicyError with list of all violations.
    """
    from app.core.config import settings  # late import to avoid circular
    require_special = settings.PASSWORD_REQUIRE_SPECIAL

    violations: list[str] = []

    if len(password) < MIN_LENGTH:
        violations.append(f"Must be at least {MIN_LENGTH} characters long.")

    if REQUIRE_UPPERCASE and not re.search(r"[A-Z]", password):
        violations.append("Must contain at least one uppercase letter.")

    if REQUIRE_LOWERCASE and not re.search(r"[a-z]", password):
        violations.append("Must contain at least one lowercase letter.")

    if REQUIRE_DIGIT and not re.search(r"\d", password):
        violations.append("Must contain at least one digit.")

    if require_special and not re.search(rf"[{re.escape(_SPECIAL_CHARS)}]", password):
        violations.append("Must contain at least one special character.")

    if password.lower() in _COMMON_PASSWORDS or password in _COMMON_PASSWORDS:
        violations.append("Password is too common. Please choose a stronger password.")

    if username and password.lower() == username.lower():
        violations.append("Password must not be the same as your username.")

    if violations:
        raise PasswordPolicyError(violations)


def password_meets_policy(password: str, username: str | None = None) -> tuple[bool, list[str]]:
    """Return (is_valid, violations) without raising."""
    try:
        validate_password(password, username)
        return True, []
    except PasswordPolicyError as e:
        return False, e.violations
