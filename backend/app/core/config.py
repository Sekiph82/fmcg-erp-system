from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from typing import List
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.development"), extra="ignore")

    # App
    PROJECT_NAME: str = "FMCG ERP"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # set to "production" in prod
    AUTO_CREATE_TABLES: bool = False
    RUN_MIGRATIONS_ON_STARTUP: bool = False

    # Security
    SECRET_KEY: str = "changeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    AUTH_COOKIE_NAME: str = "erp_access_token"
    AUTH_COOKIE_SECURE: bool = False
    AUTH_COOKIE_SAMESITE: str = "lax"
    AUTH_RETURN_TOKEN_IN_BODY: bool = False
    ERROR_TRACKING_DSN: str = ""

    # Bootstrap / seed controls
    SEED_INITIAL_ADMIN: bool = True
    SEED_DEMO_DATA: bool = False
    # DEV ONLY: when true, seed_admin re-hashes the admin password from
    # INITIAL_ADMIN_PASSWORD on every startup so the DB matches .env.development.
    # Production startup rejects this flag when set to true.
    SYNC_INITIAL_ADMIN_PASSWORD: bool = False
    INITIAL_ADMIN_USERNAME: str = "admin"
    INITIAL_ADMIN_EMAIL: str = "admin@erp.local"
    INITIAL_ADMIN_PASSWORD: str = ""
    INITIAL_ADMIN_FULL_NAME: str = "System Administrator"
    DEMO_USER_PASSWORD: str = ""

    # ── Login brute-force protection ───────────────────────────────────────────
    LOGIN_MAX_ATTEMPTS: int = 5          # failures before lockout
    LOGIN_WINDOW_SECONDS: int = 600      # 10-min rolling window
    LOGIN_LOCKOUT_SECONDS: int = 1800    # 30-min lockout

    # ── Password policy ────────────────────────────────────────────────────────
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = False  # enable in production

    # ── Session security ───────────────────────────────────────────────────────
    SESSION_INACTIVITY_TIMEOUT_MINUTES: int = 480  # 8 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://erp_user:changeme@localhost:5432/fmcg_erp"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Request timeout
    REQUEST_TIMEOUT_SECONDS: int = 120  # recommended: 60 in production

    # Connection pool
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_RECYCLE_SECONDS: int = 1800
    DATABASE_POOL_TIMEOUT_SECONDS: int = 30
    DATABASE_POOL_PRE_PING: bool = True

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # ── 2FA OTP delivery ───────────────────────────────────────────────────────
    TWO_FACTOR_EMAIL_ENABLED: bool = True
    TWO_FACTOR_SMS_ENABLED: bool = False
    OTP_EXPIRY_SECONDS: int = 300           # 5 minutes
    OTP_RESEND_COOLDOWN_SECONDS: int = 60   # 1 minute
    OTP_MAX_ATTEMPTS: int = 5
    # DEV ONLY: log OTP to console instead of sending real email/SMS.
    # Production startup rejects this flag when set to true.
    OTP_DEV_DELIVERY_MODE: bool = True

    # ── SMTP (email OTP delivery) ───────────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@erp.local"
    SMTP_USE_TLS: bool = True

    # ── SMS OTP delivery (Twilio or compatible) ────────────────────────────────
    SMS_PROVIDER: str = ""          # "twilio" or ""
    SMS_ACCOUNT_SID: str = ""       # Twilio Account SID
    SMS_AUTH_TOKEN: str = ""        # Twilio Auth Token
    SMS_SENDER_ID: str = ""         # From number/sender ID

    # ── M-Pesa / Safaricom Daraja ──────────────────────────────────────────────
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_SHORTCODE: str = ""
    MPESA_PASSKEY: str = ""
    MPESA_CALLBACK_URL: str = "https://yourapp.example.com/api/v1/integrations/mpesa/callback"
    MPESA_ENV: str = "sandbox"           # "sandbox" | "production"
    MPESA_TRANSACTION_TYPE: str = "CustomerPayBillOnline"  # or CustomerBuyGoodsOnline

    @property
    def MPESA_BASE_URL(self) -> str:
        if self.MPESA_ENV == "production":
            return "https://api.safaricom.co.ke"
        return "https://sandbox.safaricom.co.ke"

    @property
    def MPESA_CONFIGURED(self) -> bool:
        return bool(self.MPESA_CONSUMER_KEY and self.MPESA_CONSUMER_SECRET
                    and self.MPESA_SHORTCODE and self.MPESA_PASSKEY)

    # ── AI Provider ───────────────────────────────────────────────────────────
    # Set AI_PROVIDER to preferred provider. If that provider's key is missing,
    # the system auto-detects whichever key is present (anthropic → openai → gemini).
    AI_PROVIDER: str = "auto"               # "auto" | "anthropic" | "openai" | "gemini" | "mock"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.3             # lower = more deterministic for structured outputs

    # ── AI data masking (external LLM calls only) ──────────────────────────────
    AI_MASK_EXTERNAL_CONTEXT: bool = True
    AI_SEND_PRODUCT_NAMES_TO_LLM: bool = True
    AI_SEND_CUSTOMER_NAMES_TO_LLM: bool = False
    AI_SEND_SUPPLIER_NAMES_TO_LLM: bool = False
    AI_SEND_FINANCIAL_TOTALS_TO_LLM: bool = True
    AI_CONTEXT_MAX_RECORDS: int = 50

    # ── AI rate limits (requests per user per hour) ────────────────────────────
    AI_RATE_LIMIT_CHAT: int = 30
    AI_RATE_LIMIT_GENERATE: int = 10

    # ── Hybrid module enhancement (off by default — avoids unexpected LLM cost) ─
    AI_ENABLE_MODULE_LLM_ENHANCEMENT: bool = False
    AI_NL_COMMAND_EXECUTION_ENABLED: bool = False

    @property
    def AI_CONFIGURED(self) -> bool:
        if self.AI_PROVIDER == "anthropic":
            return bool(self.ANTHROPIC_API_KEY)
        if self.AI_PROVIDER == "openai":
            return bool(self.OPENAI_API_KEY)
        if self.AI_PROVIDER == "gemini":
            return bool(self.GEMINI_API_KEY)
        if self.AI_PROVIDER == "auto":
            return bool(self.ANTHROPIC_API_KEY or self.OPENAI_API_KEY or self.GEMINI_API_KEY)
        return self.AI_PROVIDER == "mock"

    @property
    def AI_ACTIVE_MODEL(self) -> str:
        """Return the model name for the currently configured provider."""
        p = self.AI_PROVIDER.lower()
        if p == "anthropic":
            return self.ANTHROPIC_MODEL
        if p == "openai":
            return self.OPENAI_MODEL
        if p == "gemini":
            return self.GEMINI_MODEL
        if p == "mock":
            return "mock-v1"
        # auto — return whichever key is present
        if self.ANTHROPIC_API_KEY:
            return self.ANTHROPIC_MODEL
        if self.OPENAI_API_KEY:
            return self.OPENAI_MODEL
        if self.GEMINI_API_KEY:
            return self.GEMINI_MODEL
        return "mock-v1"

    # ── KRA eTIMS (Kenya e-Invoice) ───────────────────────────────────────────
    # Provider/middleware decision is still pending. Final connector may be:
    #   direct KRA OSCU/VSCU API, certified middleware, or third-party service provider.
    # Do NOT use in production until KRA sandbox/provider validation is complete.
    ETIMS_PROVIDER: str = "simulation"       # "simulation" | "http"
    ETIMS_API_URL: str = ""                  # Base URL — provider/KRA-spec dependent
    # Endpoint path is provider/KRA-spec dependent — confirm before use.
    ETIMS_SALES_SUBMIT_PATH: str = "/api/method/saveSales"
    ETIMS_PIN: str = ""                      # KRA taxpayer PIN
    ETIMS_BRANCH_ID: str = ""               # Branch ID / bhfId
    ETIMS_DEVICE_SERIAL_NO: str = ""        # OSCU/VSCU device serial number
    ETIMS_ENV: str = "sandbox"              # "sandbox" | "production"

    @property
    def ETIMS_CONFIGURED(self) -> bool:
        return bool(self.ETIMS_API_URL and self.ETIMS_PIN and self.ETIMS_BRANCH_ID)

    # ── Management user seed (optional) ──────────────────────────────────────────
    # Set ERP_SEED_MANAGEMENT_USERS=true to create top-level management accounts on
    # first deploy. Only roles with both EMAIL and PASSWORD set are created.
    # ERP_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN forces a password reset on first login.
    # Production startup rejects CHANGE_ME passwords when seeding is enabled.
    ERP_SEED_MANAGEMENT_USERS: bool = False
    ERP_FORCE_PASSWORD_CHANGE_ON_FIRST_LOGIN: bool = True

    ERP_ADMIN_EMAIL: str = ""
    ERP_ADMIN_PASSWORD: str = ""
    ERP_ADMIN_FULL_NAME: str = "System Administrator"

    ERP_CEO_EMAIL: str = ""
    ERP_CEO_PASSWORD: str = ""
    ERP_CEO_FULL_NAME: str = "Chief Executive Officer"

    ERP_CTO_EMAIL: str = ""
    ERP_CTO_PASSWORD: str = ""
    ERP_CTO_FULL_NAME: str = "Chief Technology Officer"

    ERP_CMO_EMAIL: str = ""
    ERP_CMO_PASSWORD: str = ""
    ERP_CMO_FULL_NAME: str = "Chief Marketing Officer"

    ERP_COO_EMAIL: str = ""
    ERP_COO_PASSWORD: str = ""
    ERP_COO_FULL_NAME: str = "Chief Operating Officer"

    ERP_CFO_EMAIL: str = ""
    ERP_CFO_PASSWORD: str = ""
    ERP_CFO_FULL_NAME: str = "Chief Financial Officer"

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            if self.SECRET_KEY in {"changeme", "change-this-to-a-random-secret-key"} or self.SECRET_KEY.startswith("CHANGE_ME"):
                raise ValueError("SECRET_KEY must be changed from the default value in production")
            if not self.PASSWORD_REQUIRE_SPECIAL:
                raise ValueError("PASSWORD_REQUIRE_SPECIAL must be True in production")
            if self.SEED_DEMO_DATA:
                raise ValueError("SEED_DEMO_DATA must be false in production")
            if self.SEED_INITIAL_ADMIN and (not self.INITIAL_ADMIN_PASSWORD or self.INITIAL_ADMIN_PASSWORD.startswith("CHANGE_ME")):
                raise ValueError("INITIAL_ADMIN_PASSWORD is required in production when SEED_INITIAL_ADMIN=true")
            if not self.AUTH_COOKIE_SECURE:
                raise ValueError("AUTH_COOKIE_SECURE must be true in production")
            if self.SYNC_INITIAL_ADMIN_PASSWORD:
                raise ValueError(
                    "SYNC_INITIAL_ADMIN_PASSWORD=true is not allowed in production. "
                    "This flag auto-resets the admin password from env on every startup, "
                    "which is a development-only convenience. "
                    "Set SYNC_INITIAL_ADMIN_PASSWORD=false in .env.production."
                )
            if self.OTP_DEV_DELIVERY_MODE:
                raise ValueError(
                    "OTP_DEV_DELIVERY_MODE=true is not allowed in production. "
                    "This flag logs OTPs to the console instead of sending real email/SMS. "
                    "Set OTP_DEV_DELIVERY_MODE=false in .env.production."
                )
            if self.ERP_SEED_MANAGEMENT_USERS:
                mgmt = [
                    ("ERP_ADMIN", self.ERP_ADMIN_EMAIL, self.ERP_ADMIN_PASSWORD),
                    ("ERP_CEO",   self.ERP_CEO_EMAIL,   self.ERP_CEO_PASSWORD),
                    ("ERP_CTO",   self.ERP_CTO_EMAIL,   self.ERP_CTO_PASSWORD),
                    ("ERP_CMO",   self.ERP_CMO_EMAIL,   self.ERP_CMO_PASSWORD),
                    ("ERP_COO",   self.ERP_COO_EMAIL,   self.ERP_COO_PASSWORD),
                    ("ERP_CFO",   self.ERP_CFO_EMAIL,   self.ERP_CFO_PASSWORD),
                ]
                for prefix, email, password in mgmt:
                    if not email and not password:
                        continue  # intentionally skipped
                    if email and not password:
                        raise ValueError(f"{prefix}_PASSWORD is required when {prefix}_EMAIL is set")
                    if password and not email:
                        raise ValueError(f"{prefix}_EMAIL is required when {prefix}_PASSWORD is set")
                    if password.startswith("CHANGE_ME"):
                        raise ValueError(f"{prefix}_PASSWORD must not use a CHANGE_ME placeholder in production")
        return self

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, list):
            return v
        try:
            return json.loads(v)
        except Exception:
            return [i.strip() for i in str(v).split(",") if i.strip()]


settings = Settings()
