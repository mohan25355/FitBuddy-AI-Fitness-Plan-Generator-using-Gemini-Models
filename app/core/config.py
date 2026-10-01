from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "FitBuddy"
    app_version: str = "1.0.0"
    environment: str = Field(default="development", alias="ENVIRONMENT")
    secret_key: str = Field(default="change-this-secret", alias="SECRET_KEY")
    database_url: str = Field(default="sqlite:///./fitbuddy.db", alias="DATABASE_URL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_workout_model: str = Field(default="", alias="GEMINI_WORKOUT_MODEL")
    gemini_fast_model: str = Field(default="", alias="GEMINI_FAST_MODEL")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password_hash: str = Field(default="", alias="ADMIN_PASSWORD_HASH")
    csrf_cookie_name: str = "fitbuddy_csrf"
    session_cookie_name: str = "fitbuddy_session"
    request_timeout_seconds: int = 30

    @property
    def default_workout_model(self) -> str:
        return self.gemini_workout_model or "gemini-2.0-flash"

    @property
    def default_fast_model(self) -> str:
        return self.gemini_fast_model or "gemini-2.0-flash-lite"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()