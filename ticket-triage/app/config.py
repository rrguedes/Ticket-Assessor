"""
Application configuration — centralises all environment variables.
Single Responsibility: Only manages settings and their defaults.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    openai_api_key: str
    azure_devops_pat: str
    azure_devops_org_url: str
    azure_devops_project: str
    openai_model: str = "gpt-4o-mini"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return cached settings instance (avoids re-parsing env on every request)."""
    return Settings()
