from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from loguru import logger

from bot.config import get_settings
from bot.database.db import add_route, list_routes, remove_route

router = Router()
settings = get_settings()


def _is_owner(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id == settings.owner_id)


def _help_text() -> str:
    return (
        "Forward bot is running.\n\n"
        "Owner commands:\n"
        "/chat_id\n"
        "/add_route &lt;source_chat_id&gt; &lt;destination_chat_id&gt; [source_topic_id] [destination_topic_id]\n"
        "/list_routes\n"
        "/remove_route &lt;route_id&gt;\n\n"
        "Behavior:\n"
        "- Bot listens to updates from configured sources\n"
        "- Every new message is forwarded immediately"
    )


def _parse_optional_int(raw_value: str) -> int | None:
    value = raw_value.strip().lower()
    if value in {"-", "none", "null"}:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_route_args(text: str) -> tuple[int, int, int | None, int | None] | None:
    parts = text.split()
    if len(parts) not in {3, 5}:
        return None
    try:
        source_chat_id = int(parts[1])
        destination_chat_id = int(parts[2])
    except ValueError:
        return None

    if len(parts) == 3:
        return source_chat_id, destination_chat_id, None, None

    source_topic_id = _parse_optional_int(parts[3])
    destination_topic_id = _parse_optional_int(parts[4])
    if parts[3].strip() and source_topic_id is None and parts[3].strip().lower() not in {"-", "none", "null"}:
        return None
    if parts[4].strip() and destination_topic_id is None and parts[4].strip().lower() not in {"-", "none", "null"}:
        return None
    return source_chat_id, destination_chat_id, source_topic_id, destination_topic_id


def _parse_one_int(text: str) -> int | None:
    parts = text.split(maxsplit=1)
    if len(parts) != 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    if not _is_owner(message):
        await message.answer("Unauthorized. This bot accepts owner commands only.")
        return
    await message.answer(_help_text())


@router.message(F.text == "/chat_id")
async def chat_id_handler(message: Message) -> None:
    if not _is_owner(message):
        return

    if message.chat is None:
        await message.answer("Could not detect current chat.")
        return

    logger.info(
        "Owner requested /chat_id in chat {} ({})",
        message.chat.id,
        message.chat.type,
    )
    await message.answer(
        "Current chat info:\n"
        f"- chat_id: <code>{message.chat.id}</code>\n"
        f"- chat_type: <code>{message.chat.type}</code>\n"
        f"- topic_id (message_thread_id): <code>{message.message_thread_id}</code>"
    )


@router.message(F.text, F.text.startswith("/add_route"))
async def add_route_handler(message: Message) -> None:
    if not _is_owner(message):
        return

    parsed = _parse_route_args(message.text or "")
    if parsed is None:
        await message.answer(
            "Usage: /add_route &lt;source_chat_id&gt; &lt;destination_chat_id&gt; "
            "[source_topic_id] [destination_topic_id]\n"
            "Tip: use '-' for no topic"
        )
        return

    source_chat_id, destination_chat_id, source_topic_id, destination_topic_id = parsed
    route_id = await add_route(
        settings.db_path,
        source_chat_id,
        destination_chat_id,
        source_topic_id,
        destination_topic_id,
    )
    source_topic_text = "*" if source_topic_id is None else str(source_topic_id)
    destination_topic_text = "*" if destination_topic_id is None else str(
        destination_topic_id
    )
    await message.answer(
        "Route saved "
        f"(#{route_id}): {source_chat_id}[topic:{source_topic_text}] "
        f"-> {destination_chat_id}[topic:{destination_topic_text}]"
    )


@router.message(F.text == "/list_routes")
async def list_routes_handler(message: Message) -> None:
    if not _is_owner(message):
        return

    routes = await list_routes(settings.db_path)
    if not routes:
        await message.answer("No routes configured yet.")
        return

    lines = ["Configured routes:"]
    for route in routes:
        status = "active" if route.is_active else "inactive"
        source_topic = "*" if route.source_topic_id is None else route.source_topic_id
        destination_topic = (
            "*" if route.destination_topic_id is None else route.destination_topic_id
        )
        lines.append(
            f"#{route.id} | {route.source_chat_id}[topic:{source_topic}] "
            f"-> {route.destination_chat_id}[topic:{destination_topic}] | {status}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text, F.text.startswith("/remove_route"))
async def remove_route_handler(message: Message) -> None:
    if not _is_owner(message):
        return

    route_id = _parse_one_int(message.text or "")
    if route_id is None:
        await message.answer("Usage: /remove_route &lt;route_id&gt;")
        return

    deleted = await remove_route(settings.db_path, route_id)
    if not deleted:
        await message.answer(f"Route #{route_id} was not found.")
        return

    await message.answer(f"Route #{route_id} removed.")
