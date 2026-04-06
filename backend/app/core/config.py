"""
Application configuration management
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # Basic app config
    APP_NAME: str = "Terrorism Detection & Monitoring System"
    ENVIRONMENT: str = "development"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    # Database (default SQLite for local dev; use postgresql:// in production)
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/tdm.db"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # File upload
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    UPLOAD_DIR: str = "data/uploads"
    
    # ML Models
    MODEL_DIR: str = "data/models"
    
    # External APIs (configure as needed)
    NEWS_API_KEY: str = ""
    TWITTER_BEARER_TOKEN: str = ""

    # Reddit API
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "DMFOTDAM/1.0 (Threat Monitoring Research Bot)"
    REDDIT_SCAN_INTERVAL_HOURS: int = 24
    REDDIT_DEFAULT_SUBREDDITS: str = "worldnews,news,geopolitics,terrorism,extremism"
    
    # Redis for caching and background tasks
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Monitoring
    ENABLE_METRICS: bool = True
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()