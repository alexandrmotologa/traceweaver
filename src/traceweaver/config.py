"""Configuration settings for TraceWeaver."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime application settings loaded from environment or CLI."""

    model_config = SettingsConfigDict(
        env_prefix="TW_",
        case_sensitive=False,
    )

    host: str = "0.0.0.0"
    http_port: int = 4318
    grpc_port: int = 4317
    web_port: int = 8080
    db_path: str = ":memory:"
    max_spans: int = 100_000
    cors_origins: list[str] = ["*"]
    log_level: str = "INFO"


settings = Settings()
