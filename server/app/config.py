import os
from datetime import timedelta


def _database_url():
    url = os.getenv("DATABASE_URL", "sqlite:///deckforge.db")
    # Render hands out postgres:// URLs; SQLAlchemy 2 wants postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_SORT_KEYS = False

    # No fallback on purpose: the app refuses to start without a real secret.
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv("JWT_HOURS", "8")))

    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

    SCRYFALL_BASE_URL = os.getenv("SCRYFALL_BASE_URL", "https://api.scryfall.com")
    SCRYFALL_USER_AGENT = os.getenv("SCRYFALL_USER_AGENT", "Deckforge/0.1 (student project)")
    # Set SCRYFALL_MODE=fake to run fully offline against a small built-in card list.
    SCRYFALL_MODE = os.getenv("SCRYFALL_MODE", "live")
    CARD_CACHE_HOURS = int(os.getenv("CARD_CACHE_HOURS", "24"))


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    JWT_SECRET_KEY = "test-secret-key-that-is-long-enough-32b"
    SCRYFALL_MODE = "live"  # tests mock HTTP with `responses`
