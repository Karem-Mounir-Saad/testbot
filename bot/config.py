from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_path: str
    log_level: str


def _normalize_db_path(database_url: str) -> str:
    prefix = "sqlite:///"
    if database_url.startswith(prefix):
        return database_url[len(prefix) :]
    return database_url


def get_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise ValueError("BOT_TOKEN is missing. Please set it in .env")

    database_url = os.getenv("DATABASE_URL", "sqlite:///bot.db").strip()
    db_path = _normalize_db_path(database_url)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper().strip()

    return Settings(bot_token=bot_token, db_path=db_path, log_level=log_level)
