from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    GROQ_API_KEY: str

    GEMINI_API_KEY: Optional[str] = None

    LLM_MODEL: str = "llama-3.3-70b-versatile"


settings = Settings()