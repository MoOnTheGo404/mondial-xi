from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="KICKOFF_", extra="ignore")

    database_url: str = "sqlite:///./data/kickoff.db"
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    weather_enabled: bool = True
    max_simulations: int = 20_000
    environment: str = "development"


settings = Settings()
