"""
Application configuration loaded from environment variables / .env file.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global settings. Read once, cached via get_settings()."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Environment ---
    APP_NAME: str = "Terrorism Detection & Monitoring System"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    API_V1_PREFIX: str = "/api/v1"
    TIMEZONE: str = "Australia/Sydney"

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- CORS ---
    ALLOWED_HOSTS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # --- MongoDB Atlas ---
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "tdm_db"

    # --- JWT / Auth ---
    SECRET_KEY: str = "CHANGE-ME-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12h

    # --- Uploads ---
    MAX_FILE_SIZE: int = 52_428_800  # 50 MB
    UPLOAD_DIR: str = "data/uploads"

    # --- ML model (HuggingFace pretrained) ---
    # HateBERT is pre-trained on Reddit hate speech (RAL-E dataset), providing
    # much better domain fit for extremism detection than generic toxicity
    # models. Falls back to RoBERTa-hate if HateBERT fails to load.
    HF_MODEL_NAME: str = "GroNLP/hateBERT"
    HF_FALLBACK_MODEL_NAME: str = "cardiffnlp/twitter-roberta-base-hate"
    HF_MODEL_CACHE: str = "data/models"
    ML_DEVICE: str = "cpu"              # "cpu" or "cuda"
    ML_MAX_CHARS: int = 4000            # per-chunk cap sent to the model

    # --- Reddit API ---
    REDDIT_CLIENT_ID: str = ""
    REDDIT_CLIENT_SECRET: str = ""
    REDDIT_USER_AGENT: str = "TDM-Research-Bot/1.0"
    REDDIT_DEFAULT_SUBREDDITS: str = "news,worldnews,CredibleDefense"

    # --- RSS + Telegram (real-time news + channel bridges) ---
    # Users can add/remove more via the /monitoring/sources API.
    DEFAULT_RSS_FEEDS: List[str] = [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://feeds.reuters.com/reuters/worldNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    ]
    # Public RSSHub instance for Telegram channels. Self-host for production.
    TELEGRAM_RSS_BRIDGE: str = "https://rsshub.app/telegram/channel/"

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str = ""

    # --- SMTP (email OTP) ---
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    OTP_EXPIRE_MINUTES: int = 10

    # --- Monitoring cadence / thresholds ---
    COLLECTOR_INTERVAL_SECONDS: int = 300     # poll every 5 min
    ALERT_THRESHOLD: float = 0.6              # flag items with score >= this


@lru_cache()
def get_settings() -> Settings:
    return Settings()
