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
        "/add_route &lt;source_chat_id&gt; &lt;destination_chat_id&gt;\n"
        "/list_routes\n"
        "/remove_route &lt;route_id&gt;\n\n"
        "Behavior:\n"
        "- Bot listens to updates from configured sources\n"
        "- Every new message is forwarded immediately"
    )


def _parse_two_ints(text: str) -> tuple[int, int] | None:
    parts = text.split(maxsplit=2)
    if len(parts) != 3:
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


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
        f"- chat_type: <code>{message.chat.type}</code>"
    )


@router.message(F.text, F.text.startswith("/add_route"))
async def add_route_handler(message: Message) -> None:
    if not _is_owner(message):
        return

    parsed = _parse_two_ints(message.text or "")
    if parsed is None:
        await message.answer(
            "Usage: /add_route &lt;source_chat_id&gt; &lt;destination_chat_id&gt;"
        )
        return

    source_chat_id, destination_chat_id = parsed
    route_id = await add_route(settings.db_path, source_chat_id, destination_chat_id)
    await message.answer(
        f"Route saved (#{route_id}): {source_chat_id} -> {destination_chat_id}"
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
        lines.append(
            f"#{route.id} | {route.source_chat_id} -> {route.destination_chat_id} | {status}"
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
