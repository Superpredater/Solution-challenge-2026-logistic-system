from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://scuser:scpassword@localhost:5432/supplychain"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_group_id: str = "supply-chain-default"

    # Auth
    secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "RS256"
    jwt_expiry_minutes: int = 60

    # External APIs
    gemini_api_key: Optional[str] = None

    # Environment
    environment: str = "development"
    log_level: str = "INFO"


settings = Settings()
