from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from typing import List
import json
import math


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", ".env.development"), extra="ignore")

    # App
    PROJECT_NAME: str = "FMCG ERP"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"  # set to "production" in prod
    RUN_MIGRATIONS_ON_STARTUP: bool = False

    # Security
    SECRET_KEY: str = "changeme"
    # Keep this stable across JWT/application SECRET_KEY changes. Set a distinct
    # high-entropy value in production and back it up like other encryption keys.
    WEBHOOK_SECRET_ENCRYPTION_KEY: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours
    AUTH_COOKIE_NAME: str = "erp_access_token"
    REFRESH_TOKEN_COOKIE_NAME: str = "erp_refresh_token"
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
    REDIS_PASSWORD: str = ""  # required in production; empty = no auth (dev only)

    # Request timeout
    REQUEST_TIMEOUT_SECONDS: int = 120  # recommended: 60 in production

    # Connection pool
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_RECYCLE_SECONDS: int = 1800
    DATABASE_POOL_TIMEOUT_SECONDS: int = 30
    DATABASE_POOL_PRE_PING: bool = True

    # Every API worker polls; delivery rows use SKIP LOCKED for safe sharing.
    WEBHOOK_DISPATCH_INTERVAL_SECONDS: float = 5.0
    WEBHOOK_DISPATCH_BATCH_SIZE: int = 50

    # Document binaries use a persistent local volume by default. Downloads
    # remain quarantined until a configured malware scanner reports CLEAN.
    DOCUMENT_STORAGE_PROVIDER: str = "local"
    DOCUMENT_STORAGE_PATH: str = "data/documents"
    DOCUMENT_MAX_UPLOAD_BYTES: int = 26_214_400  # 25 MiB
    MEDIA_STORAGE_PATH: str = "data/media"           # M46 CMS video/audio (local)
    SLACK_SIGNING_SECRET: str = ""                    # M47 Slack interactive approvals (NOT_CONFIGURED when empty)
    META_PIXEL_ID: str = ""                           # M47 Meta CAPI conversions
    GOOGLE_ADS_CONVERSION_ACTION: str = ""            # M47 customers/<id>/conversionActions/<id>
    MAIL_AUTHSERV_ID: str = ""                        # M47: our mail server's Authentication-Results authserv-id
    METRICS_TOKEN: str = ""                           # M47: /metrics needs this bearer token when set; else loopback only
    MEDIA_MAX_UPLOAD_BYTES: int = 209_715_200        # 200 MiB
    DOCUMENT_CLAMAV_HOST: str = ""
    DOCUMENT_CLAMAV_PORT: int = 3310
    DOCUMENT_CLAMAV_TIMEOUT_SECONDS: int = 20

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
    MAIL_ALLOW_PRIVATE_HOSTS: bool = False  # mailbox IMAP/SMTP may point at private addresses (self-hosted mail server)
    CALL_RECORDING_RETENTION_DAYS: int = 90   # call recordings: link removed after this many days
    CALL_TRANSCRIPTION_ENABLED: bool = False
    CONVERSATION_INTELLIGENCE_ENABLED: bool = False  # opt-in: analyse consented transcripts (M36.S05.T004)   # only switch on where recording transcription is lawful and disclosed
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "noreply@erp.local"
    SMTP_USE_TLS: bool = True
    # CRM outbound e-mail (M36): outbox delivery is off until explicitly enabled; queued mail then waits
    CRM_OUTBOUND_EMAIL_ENABLED: bool = False
    CRM_OUTBOUND_MAX_PER_TICK: int = 30            # delivery rate limit per 15 s worker tick
    PUBLIC_APP_URL: str = "http://localhost:3000"  # used in unsubscribe links
    # M48.S01.T022 unsubscribe / consent-confirmation link signing. Blank = SECRET_KEY (links already sent keep working).
    # To rotate: move the old value (or the old SECRET_KEY) into UNSUBSCRIBE_PREVIOUS_SECRETS (comma list), set a new one.
    UNSUBSCRIBE_SECRET: str = ""
    UNSUBSCRIBE_PREVIOUS_SECRETS: str = ""
    CRM_CONSENT_CONFIRM_TTL_HOURS: int = 72         # double opt-in link lifetime
    # M48.S01.T022 retention (days); the daily purge job deletes older rows
    CRM_LEAD_SUBMISSION_RETENTION_DAYS: int = 730
    CRM_EMAIL_EVENT_RETENTION_DAYS: int = 395
    CRM_LANDING_EVENT_RETENTION_DAYS: int = 395
    CRM_DOCUMENT_VIEW_RETENTION_DAYS: int = 730
    CRM_SIGNER_CODE_RETENTION_DAYS: int = 30        # counted from the code's expiry
    CRM_CONSENT_PENDING_RETENTION_DAYS: int = 30    # unconfirmed double opt-in requests
    # M43.S01.T006 e-mail engagement tracking: off unless enabled; then only for e-mails that opt in
    CRM_EMAIL_TRACKING_ENABLED: bool = False
    CRM_TRACKING_LINK_DOMAINS: str = ""
    CRM_CONTACT_EMAIL_CAP_PER_WEEK: int = 0
    # M44.S01.T011 signed mail-event webhooks (blank = not configured: events refused)
    MAIL_EVENTS_MAILGUN_SIGNING_KEY: str = ""
    MAIL_EVENTS_SENDGRID_PUBLIC_KEY: str = ""        # base64 DER (as shown in the SendGrid settings)
    MAIL_EVENTS_GENERIC_SECRET: str = ""
    MARKETING_EMAIL_APPROVAL_REQUIRED: bool = False   # M44.S01.T012: campaigns need a second editor's approval
    # M44.S01.T009 first-party web analytics: events kept this many days, then purged
    WEB_ANALYTICS_RETENTION_DAYS: int = 395
    AUDIENCE_EXPORT_ENABLED: bool = False   # M44.S01.T010: hashed customer-list export off by default
    # M44.S01.T002–T005 ad platforms: blank token = NOT_CONFIGURED. Live campaign publishing is never enabled by config.
    ADS_MAX_DAILY_BUDGET: float = 50.0      # guardrail per draft, account currency
    META_ADS_API_URL: str = "https://graph.facebook.com"
    META_ADS_API_VERSION: str = "v27.0"     # current Graph version 2026-11 (M48 capability matrix)
    META_ADS_ACCESS_TOKEN: str = ""
    GOOGLE_ADS_API_URL: str = "https://googleads.googleapis.com"
    GOOGLE_ADS_API_VERSION: str = "v26"       # Google Ads API v26 (2026-11)
    GOOGLE_ADS_DEVELOPER_TOKEN: str = ""
    GOOGLE_ADS_ACCESS_TOKEN: str = ""
    GOOGLE_ADS_LOGIN_CUSTOMER_ID: str = ""
    LINKEDIN_ADS_API_URL: str = "https://api.linkedin.com"
    LINKEDIN_ADS_VERSION: str = "202611"     # YYYYMM, sent as LinkedIn-Version (each version supported ~1 year)
    LINKEDIN_ADS_ACCESS_TOKEN: str = ""
    LINKEDIN_ADS_ACCESS_TIER: str = "development"   # development | standard
    TIKTOK_ADS_API_URL: str = "https://business-api.tiktok.com"
    TIKTOK_ADS_ACCESS_TOKEN: str = ""
    TIKTOK_ADS_APP_SECRET: str = ""
    # M44.S01.T006–T008 social: publishing stays off until the owner enables it; tokens per network (blank = manual export)
    SOCIAL_PUBLISHING_ENABLED: bool = False
    # M48: live provider actions stay off until owner activation (each also needs credentials + approval)
    TIKTOK_APP_AUDITED: bool = False             # unaudited TikTok apps may only post SELF_ONLY
    TIKTOK_VERIFIED_URL_PREFIXES: str = ""       # comma list of verified PULL_FROM_URL prefixes/domains
    TIKTOK_CLIENT_SECRET: str = ""               # signs TikTok webhooks (TikTok-Signature)
    SOCIAL_PUBLISH_TIMEOUT_MINUTES: int = 30
    SOCIAL_STATUS_POLL_SECONDS: int = 15
    SOCIAL_STATUS_BACKOFF_SECONDS: float = 1.0
    MARKETING_DIRECT_SEND_DAILY_CAP: int = 200    # M48.S01.T023 F4: ABM / design single-send recipients per editor per 24 h
    # M49 provider settings (blank = not configured; live use also needs PROVIDER_EGRESS=live and owner activation)
    CALENDAR_WEBHOOK_BASE_URL: str = ""
    VOICE_TWILIO_ACCOUNT_SID: str = ""
    VOICE_TWILIO_AUTH_TOKEN: str = ""
    VOICE_TWILIO_PHONE_NUMBER: str = ""
    VOICE_TWILIO_BASE_URL: str = "https://api.twilio.com"
    TRANSCRIPTION_OPENAI_API_KEY: str = ""
    TRANSCRIPTION_OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    TRANSCRIPT_RETENTION_DAYS: int = 90
    YOUTUBE_SOCIAL_ACCESS_TOKEN: str = ""
    YOUTUBE_API_URL: str = "https://www.googleapis.com"
    YOUTUBE_UNVERIFIED_PRIVATE_ONLY: bool = True
    YOUTUBE_UPLOAD_QUOTA_PER_DAY: int = 100
    YOUTUBE_CHUNK_BYTES: int = 8388608
    X_SOCIAL_ACCESS_TOKEN: str = ""
    X_API_URL: str = "https://api.x.com"
    META_APP_ID: str = ""
    META_VIDEO_API_URL: str = ""
    META_RUPLOAD_URL: str = ""
    SOCIAL_ITEM_RETENTION_DAYS: int = 365
    SOCIAL_LISTEN_POLL_MINUTES: int = 15
    GOOGLE_DATA_MANAGER_API_URL: str = "https://datamanager.googleapis.com"
    GOOGLE_CUSTOMER_MATCH_TOS_ACCEPTED: bool = False
    MARKETING_STUDIO_BUDGET_CAP: float = 50000
    # M50 (blank/off = not configured; live provider use also needs PROVIDER_EGRESS=live and owner activation)
    BRAVE_SEARCH_API_KEY: str = ""
    BRAVE_SEARCH_BASE_URL: str = ""          # blank = official https://api.search.brave.com/res/v1/web/search
    PDL_API_KEY: str = ""
    PDL_BASE_URL: str = "https://api.peopledatalabs.com"
    M50_FETCH_MAX_BYTES: int = 1000000
    M50_FETCH_TIMEOUT: float = 8.0
    M50_FETCH_MAX_REDIRECTS: int = 3
    SERVICE_AGENT_LLM_ENABLED: bool = False
    SERVICE_AGENT_LLM_MAX_CALLS_PER_SESSION: int = 20
    SERVICE_AGENT_LLM_MAX_CALLS_PER_DAY: int = 500
    SERVICE_AGENT_HISTORY_TURNS: int = 6
    ADDIN_ALLOWED_ORIGINS: list[str] = []
    ADDIN_GRANT_MAX_DAYS: int = 30
    SERVICE_AGENT_SAFETY_PER_IP_HOUR: int = 3
    ADS_LIVE_MUTATIONS: bool = False             # M48.S01.T001–T004 live ad mutations
    CARD_PAYMENTS_LIVE_ENABLED: bool = False     # M48.S01.T010 Pesapal live money
    WAREHOUSE_LIVE_ENABLED: bool = False         # M48.S01.T007/T008 Snowflake/BigQuery live sync
    ESIGN_LIVE_ENABLED: bool = False             # M48.S01.T009 DocuSign/Adobe Sign live sending
    META_PAGE_ACCESS_TOKEN: str = ""             # Facebook Page + Instagram professional account (Graph API)
    META_APP_SECRET: str = ""                    # signs Meta webhooks (X-Hub-Signature-256)
    META_WEBHOOK_VERIFY_TOKEN: str = ""
    LINKEDIN_SOCIAL_ACCESS_TOKEN: str = ""       # w_organization_social
    TIKTOK_SOCIAL_ACCESS_TOKEN: str = ""         # Content Posting API (video.publish)
    TIKTOK_SOCIAL_API_URL: str = "https://open.tiktokapis.com"
    # M44.S01.T013 Slack incoming webhook for deal / ticket / approval notices (blank = not configured)
    SLACK_WEBHOOK_URL: str = ""
    # M42 business cards: shared POVU brand content (cover video, logo, videos, gallery, catalogue). Owner decision
    # 2026-11-24: the GitHub Pages card repo is the source; point this at a self-hosted copy later if wanted.
    CARD_ASSETS_BASE_URL: str = "https://sekiph82.github.io/SekipHayit"
    PUBLIC_API_URL: str = "http://localhost:8000"  # used for one-click List-Unsubscribe-Post
    # M43.S01.T008 voice provider (blank = no provider: tel: fallback); callbacks carry VOICE_CALLBACK_SECRET
    VOICE_PROVIDER: str = ""
    VOICE_AT_USERNAME: str = ""
    VOICE_AT_API_KEY: str = ""
    VOICE_AT_PHONE_NUMBER: str = ""
    VOICE_AT_BASE_URL: str = "https://voice.africastalking.com"
    VOICE_CALLBACK_SECRET: str = ""
    # M43.S01.T009 transcription adapter: "" (off) | "local" (offline engine if installed) | "http" (configured endpoint)
    TRANSCRIPTION_PROVIDER: str = ""
    TRANSCRIPTION_HTTP_URL: str = ""
    TRANSCRIPTION_HTTP_KEY: str = ""

    # ── Provider egress + delegated OAuth (M43.S00.T004) ─────────────────────
    # PROVIDER_EGRESS: live | local | off; blank = live in production, local (simulators only) elsewhere.
    PROVIDER_EGRESS: str = ""
    OAUTH_REDIRECT_BASE_URL: str = ""          # blank = PUBLIC_API_URL; callback is /api/v1/integrations/oauth/callback
    GOOGLE_OAUTH_CLIENT_ID: str = ""
    GOOGLE_OAUTH_CLIENT_SECRET: str = ""
    GOOGLE_OAUTH_AUTH_URL: str = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_OAUTH_TOKEN_URL: str = "https://oauth2.googleapis.com/token"
    GOOGLE_OAUTH_REVOKE_URL: str = "https://oauth2.googleapis.com/revoke"
    GOOGLE_OAUTH_USERINFO_URL: str = "https://openidconnect.googleapis.com/v1/userinfo"
    MICROSOFT_OAUTH_CLIENT_ID: str = ""
    MICROSOFT_OAUTH_CLIENT_SECRET: str = ""
    MICROSOFT_OAUTH_TENANT: str = "common"
    MICROSOFT_LOGIN_BASE_URL: str = "https://login.microsoftonline.com"
    MICROSOFT_GRAPH_BASE_URL: str = "https://graph.microsoft.com/v1.0"
    GOOGLE_GMAIL_API_URL: str = "https://gmail.googleapis.com/gmail/v1"
    GOOGLE_CALENDAR_API_URL: str = "https://www.googleapis.com/calendar/v3"

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
    # Shared secret appended to MPESA_CALLBACK_URL as ?token=...; callbacks without it are rejected.
    MPESA_CALLBACK_SECRET: str = ""
    # Meta app secret used to verify X-Hub-Signature-256 on WhatsApp webhooks.
    WHATSAPP_APP_SECRET: str = ""
    # Meta WhatsApp Cloud API sender for customer notices (set from Integrations → Provider keys or .env)
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_ACCESS_TOKEN: str = ""
    # Shopify custom app (Admin API access token; never stored in the database).
    SHOPIFY_SHOP_DOMAIN: str = ""          # <store>.myshopify.com
    SHOPIFY_ACCESS_TOKEN: str = ""
    SHOPIFY_API_VERSION: str = "2024-10"
    SHOPIFY_LOCATION_ID: str = ""          # Shopify location whose stock the ERP sets
    SHOPIFY_CUSTOMER_ID: str = ""          # ERP customer that web orders are booked against
    SHOPIFY_WAREHOUSE_ID: str = ""         # ERP warehouse for web orders and stock

    # MQTT -> IoT ingest bridge (broker-agnostic). Empty broker URL disables it.
    MQTT_BROKER_URL: str = ""              # mqtt://host:1883 or mqtts://host:8883 (TLS required in production)
    MQTT_USERNAME: str = ""
    MQTT_PASSWORD: str = ""
    MQTT_CA_FILE: str = ""                 # private CA bundle for mqtts; system CAs when empty
    MQTT_TOPICS: str = "fmcg/iot/#"        # comma-separated topic filters, QoS 1
    MQTT_CLIENT_ID: str = ""               # keep empty with several workers: one fixed id makes the broker kick them in turn
    MQTT_SHARED_GROUP: str = "fmcg-erp"    # $share group so API workers split messages; empty disables
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
    ANTHROPIC_MODEL: str = "claude-sonnet-5-5"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-latest"
    AI_MAX_TOKENS: int = 16000
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
            if len(self.SECRET_KEY.encode("utf-8")) < 32:
                raise ValueError("SECRET_KEY must contain at least 32 UTF-8 bytes for HS256 in production")
            webhook_key = self.WEBHOOK_SECRET_ENCRYPTION_KEY
            if len(webhook_key.encode("utf-8")) < 32:
                raise ValueError("WEBHOOK_SECRET_ENCRYPTION_KEY must contain at least 32 UTF-8 bytes in production")
            if webhook_key == self.SECRET_KEY:
                raise ValueError("WEBHOOK_SECRET_ENCRYPTION_KEY must be distinct from SECRET_KEY")
            normalized_webhook_key = webhook_key.strip().lower()
            webhook_weak_markers = (
                "changeme",
                "change-this",
                "secret",
                "password",
                "example",
                "placeholder",
                "development",
                "production",
                "test",
            )
            if any(marker in normalized_webhook_key for marker in webhook_weak_markers):
                raise ValueError("WEBHOOK_SECRET_ENCRYPTION_KEY must not contain placeholder or example text in production")
            for period in range(1, min(len(webhook_key), 16) + 1):
                repeated = webhook_key[:period] * (len(webhook_key) // period)
                if len(webhook_key) % period == 0 and webhook_key == repeated:
                    raise ValueError("WEBHOOK_SECRET_ENCRYPTION_KEY must not be a repeated pattern in production")
            normalized_key = self.SECRET_KEY.strip().lower()
            known_weak_markers = (
                "changeme",
                "change-this",
                "secret",
                "password",
                "example",
                "placeholder",
                "development",
                "production",
                "test",
            )
            if any(marker in normalized_key for marker in known_weak_markers):
                raise ValueError("SECRET_KEY must not contain placeholder or example text in production")
            for period in range(1, min(len(self.SECRET_KEY), 16) + 1):
                repeated = self.SECRET_KEY[:period] * (len(self.SECRET_KEY) // period)
                if len(self.SECRET_KEY) % period == 0 and self.SECRET_KEY == repeated:
                    raise ValueError("SECRET_KEY must not be a repeated pattern in production")
            if not self.PASSWORD_REQUIRE_SPECIAL:
                raise ValueError("PASSWORD_REQUIRE_SPECIAL must be True in production")
            if self.SEED_DEMO_DATA:
                raise ValueError("SEED_DEMO_DATA must be false in production")
            if self.SEED_INITIAL_ADMIN and (not self.INITIAL_ADMIN_PASSWORD or self.INITIAL_ADMIN_PASSWORD.startswith("CHANGE_ME")):
                raise ValueError("INITIAL_ADMIN_PASSWORD is required in production when SEED_INITIAL_ADMIN=true")
            if self.SEED_INITIAL_ADMIN:   # M47.S01.T003: documented/default passwords are refused in production
                pw = self.INITIAL_ADMIN_PASSWORD or ""
                weak = {"admin1234!", "admin123!", "admin1234", "password1!", "changeme1!", "povu1234!"}
                if pw.lower() in weak or len(pw) < 12:
                    raise ValueError("INITIAL_ADMIN_PASSWORD must be a unique password of at least 12 characters in production")
            if not self.AUTH_COOKIE_SECURE:
                raise ValueError("AUTH_COOKIE_SECURE must be true in production")
            if self.CRM_OUTBOUND_EMAIL_ENABLED:   # M48.S01.T022: links in sent mail must be public https URLs
                from urllib.parse import urlparse
                for name in ("PUBLIC_APP_URL", "PUBLIC_API_URL"):
                    u = urlparse(getattr(self, name) or "")
                    host = (u.hostname or "").lower()
                    local = host in {"localhost", "127.0.0.1", "::1", "0.0.0.0"} or host.endswith(".localhost")
                    if u.scheme != "https" or not host or local:
                        raise ValueError(f"{name} must be a public https URL in production when CRM_OUTBOUND_EMAIL_ENABLED=true")
            if self.UNSUBSCRIBE_SECRET and len(self.UNSUBSCRIBE_SECRET.encode("utf-8")) < 32:
                raise ValueError("UNSUBSCRIBE_SECRET must contain at least 32 UTF-8 bytes in production")
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
            if not self.REDIS_PASSWORD or self.REDIS_PASSWORD.startswith("CHANGE_ME"):
                raise ValueError("REDIS_PASSWORD must be set to a strong value in production")
            if self.TWO_FACTOR_EMAIL_ENABLED and not self.SMTP_HOST:
                raise ValueError(
                    "SMTP_HOST must be configured in production when TWO_FACTOR_EMAIL_ENABLED=true. "
                    "Set SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_FROM_EMAIL in .env.production, "
                    "or set TWO_FACTOR_EMAIL_ENABLED=false to disable email OTP."
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

    @field_validator("REFRESH_TOKEN_EXPIRE_DAYS")
    @classmethod
    def validate_refresh_token_expiry(cls, value: int) -> int:
        if value < 1:
            raise ValueError("REFRESH_TOKEN_EXPIRE_DAYS must be at least 1")
        return value

    @field_validator("SESSION_INACTIVITY_TIMEOUT_MINUTES")
    @classmethod
    def validate_session_inactivity_timeout(cls, value: int) -> int:
        if value < 1:
            raise ValueError("SESSION_INACTIVITY_TIMEOUT_MINUTES must be at least 1")
        return value

    @field_validator("WEBHOOK_DISPATCH_INTERVAL_SECONDS")
    @classmethod
    def validate_webhook_dispatch_interval(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("WEBHOOK_DISPATCH_INTERVAL_SECONDS must be finite and positive")
        return value

    @field_validator("WEBHOOK_DISPATCH_BATCH_SIZE")
    @classmethod
    def validate_webhook_dispatch_batch_size(cls, value: int) -> int:
        if value < 1:
            raise ValueError("WEBHOOK_DISPATCH_BATCH_SIZE must be at least 1")
        return value

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
