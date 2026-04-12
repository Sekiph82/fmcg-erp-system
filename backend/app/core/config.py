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
    AI_PROVIDER: str = "anthropic"           # "anthropic" | "openai" | "mock"
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    AI_MAX_TOKENS: int = 4096
    AI_TEMPERATURE: float = 0.3             # lower = more deterministic for structured outputs

    @property
    def AI_CONFIGURED(self) -> bool:
        if self.AI_PROVIDER == "anthropic":
            return bool(self.ANTHROPIC_API_KEY)
        if self.AI_PROVIDER == "openai":
            return bool(self.OPENAI_API_KEY)
        return self.AI_PROVIDER == "mock"

    def parse_cors(self, v: str) -> List[str]:
        try:
            return json.loads(v)
        except Exception:
            return [i.strip() for i in v.split(",")]


settings = Settings()
