from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    bot_token: str
    db_path: str
    log_level: str
    owner_id: int
    route_manager_ids: tuple[int, ...]
    telethon_api_id: int | None
    telethon_api_hash: str | None
    telethon_session: str
    telethon_watch_chat_ids: tuple[int, ...]


def _parse_chat_ids(raw_value: str, var_name: str) -> tuple[int, ...]:
    cleaned = raw_value.strip()
    if not cleaned:
        return tuple()

    values: list[int] = []
    for part in cleaned.split(","):
        item = part.strip()
        if not item:
            continue
        try:
            values.append(int(item))
        except ValueError as exc:
            raise ValueError(
                f"{var_name} must be a comma-separated list of integers"
            ) from exc
    return tuple(values)


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

    route_manager_ids = _parse_chat_ids(
        os.getenv("ROUTE_MANAGER_IDS", ""),
        "ROUTE_MANAGER_IDS",
    )

    telethon_api_id_raw = os.getenv("TELETHON_API_ID", "").strip()
    telethon_api_hash = os.getenv("TELETHON_API_HASH", "").strip() or None
    telethon_session = os.getenv("TELETHON_SESSION", "telethon_session").strip()
    telethon_watch_chat_ids = _parse_chat_ids(
        os.getenv("TELETHON_WATCH_CHAT_IDS", ""),
        "TELETHON_WATCH_CHAT_IDS",
    )

    if bool(telethon_api_id_raw) != bool(telethon_api_hash):
        raise ValueError(
            "TELETHON_API_ID and TELETHON_API_HASH must both be set (or both omitted)"
        )

    telethon_api_id: int | None = None
    if telethon_api_id_raw:
        try:
            telethon_api_id = int(telethon_api_id_raw)
        except ValueError as exc:
            raise ValueError("TELETHON_API_ID must be an integer") from exc

    return Settings(
        bot_token=bot_token,
        db_path=db_path,
        log_level=log_level,
        owner_id=owner_id,
        route_manager_ids=route_manager_ids,
        telethon_api_id=telethon_api_id,
        telethon_api_hash=telethon_api_hash,
        telethon_session=telethon_session,
        telethon_watch_chat_ids=telethon_watch_chat_ids,
    )
