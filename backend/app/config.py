"""Central configuration loaded from environment / .env file."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Groq
    groq_api_key: str = "gsk_missing_key"
    groq_model: str = "gemma2-9b-it"

    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/hcp_crm"

    # CORS
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
