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
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    def parse_cors(self, v: str) -> List[str]:
        try:
            return json.loads(v)
        except Exception:
            return [i.strip() for i in v.split(",")]


settings = Settings()
