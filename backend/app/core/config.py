from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_NAME: str = "StreamTube API"
    APP_ENV: Literal["development", "production", "test"] = "development"
    API_V1_PREFIX: str = "/api/v1"

    # Security & JWT
    SECRET_KEY: str = "dev-insecure-change-me-in-production-32bytes"
    MEDIA_SIGNING_SECRET: str = "dev-media-secret-change-me-in-production-32b"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14
    MEDIA_TOKEN_EXPIRE_SECONDS: int = 900  # 15 minutes
    COOKIE_SECURE: bool = False  # Set True behind HTTPS terminator

    # CORS
    CORS_ORIGINS: str = "http://localhost,http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"

    # Database
    DATABASE_URL: str = "postgresql+psycopg://streamtube:streamtube@postgres:5432/streamtube"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"
    TRANSCODE_QUEUE_NAME: str = "streamtube:transcode"
    ENABLE_BACKGROUND_WORKER: bool = True

    # Storage (s3 / local)
    STORAGE_BACKEND: Literal["s3", "local"] = "s3"
    LOCAL_STORAGE_PATH: str = "./storage_data"
    S3_ENDPOINT_URL: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "streamtube-media"
    S3_REGION: str = "us-east-1"

    # Upload limits
    MAX_VIDEO_SIZE_BYTES: int = 500 * 1024 * 1024  # 500 MB
    MAX_THUMBNAIL_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # Rate limits
    RATE_LIMIT_ENABLED: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
