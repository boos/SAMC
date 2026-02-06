"""
Application configuration using Pydantic Settings.

Loads configuration from environment variables (.env file).
"""

from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Project Info
    PROJECT_NAME: str = "Structured Adaptive Multi-Cycle (SAMC) Training Periodization."
    VERSION: str = "0.1.0"
    AUTHORS: List[str] = ["Roberto Martelloni", "Claude"]
    AUTHORS_EMAILS: List[str] = ["rmartelloni@gmail.com", "N.A."]
    PROJECT_URL: str = "https://github.com/boos/SAMC"

    DEBUG: bool = True

    # Database
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432
    DATABASE_DBNAME: str = "postgres"

    TIMESCALEDB_ENABLED: bool = True

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # MCP (Phase 3)
    MCP_ENABLED: bool = False
    MCP_PORT: int = 8001

    # Wearable Integrations (Phase 2)
    GARMIN_EMAIL: str = ""
    GARMIN_PASSWORD: str = ""
    OURA_ACCESS_TOKEN: str = ""
    WHOOP_ACCESS_TOKEN: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


# Global settings instance
settings = Settings()
