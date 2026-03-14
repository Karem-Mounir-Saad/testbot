from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_path: str
    log_level: str
    owner_id: int


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
    owner_id_raw = os.getenv("OWNER_ID", "").strip()
    if not owner_id_raw:
        raise ValueError("OWNER_ID is missing. Please set it in .env")

    try:
        owner_id = int(owner_id_raw)
    except ValueError as exc:
        raise ValueError("OWNER_ID must be an integer Telegram user id") from exc

    return Settings(
        bot_token=bot_token,
        db_path=db_path,
        log_level=log_level,
        owner_id=owner_id,
    )
