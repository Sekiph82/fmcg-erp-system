from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import json


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    PROJECT_NAME: str = "FMCG ERP"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "changeme"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8  # 8 hours

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://erp_user:changeme@localhost:5432/fmcg_erp"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://orange-system-x5p7vqvxrq66f66xw-3000.app.github.dev",
        "https://orange-system-x5p7vqvxrq66f66xw-8000.app.github.dev",
    ]

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

    def parse_cors(self, v: str) -> List[str]:
        try:
            return json.loads(v)
        except Exception:
            return [i.strip() for i in v.split(",")]


settings = Settings()
