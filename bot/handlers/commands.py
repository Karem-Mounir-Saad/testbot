from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from loguru import logger

from bot.config import get_settings
from bot.database.db import (
    add_route_for_user,
    is_route_manager,
    list_routes_for_user,
    remove_all_routes,
    remove_route_for_user,
)

router = Router()
settings = get_settings()


def _is_owner(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id == settings.owner_id)


async def _is_manager(message: Message) -> bool:
    if message.from_user is None:
        return False
    return await is_route_manager(settings.db_path, message.from_user.id)


async def _can_manage_routes(message: Message) -> bool:
    return _is_owner(message) or await _is_manager(message)


def _help_text() -> str:
    return (
        "Forward bot is running.\n\n"
        "Commands (owner + route managers):\n"
        "/chat_id\n"
        "/add_route &lt;source_chat_id&gt; &lt;destination_chat_id&gt; [source_topic_id] [destination_topic_id]\n"
        "/list_routes\n"
        "/remove_route &lt;route_id&gt;\n"
        "Owner-only: /remove_all_routes\n\n"
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
    if not await _can_manage_routes(message):
        await message.answer(
            "Unauthorized. This bot accepts owner and configured route managers only."
        )
        return
    await message.answer(_help_text())


@router.message(F.text == "/chat_id")
async def chat_id_handler(message: Message) -> None:
    if not await _can_manage_routes(message):
        return

    if message.chat is None:
        await message.answer("Could not detect current chat.")
        return

    logger.info(
        "Authorized user requested /chat_id in chat {} ({})",
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
    if message.from_user is None:
        return

    caller_id = message.from_user.id
    is_owner = _is_owner(message)
    is_manager = await _is_manager(message)
    if not is_owner and not is_manager:
        await message.answer("You are not allowed to add routes.")
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
    status, route_id = await add_route_for_user(
        db_path=settings.db_path,
        source_chat_id=source_chat_id,
        destination_chat_id=destination_chat_id,
        source_topic_id=source_topic_id,
        destination_topic_id=destination_topic_id,
        created_by_user_id=caller_id,
        is_owner=is_owner,
    )
    if status == "forbidden":
        await message.answer(
            f"Route already exists as #{route_id} and was created by another user. "
            "Only owner can overwrite that route."
        )
        return

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
    if message.from_user is None:
        return

    caller_id = message.from_user.id
    is_owner = _is_owner(message)
    is_manager = await _is_manager(message)
    if not is_owner and not is_manager:
        await message.answer("You are not allowed to list routes.")
        return

    routes = await list_routes_for_user(settings.db_path, caller_id, is_owner)
    if not routes:
        await message.answer("No routes configured yet.")
        return

    title = "Configured routes (all):" if is_owner else "Configured routes (your routes only):"
    lines = [title]
    for route in routes:
        status = "active" if route.is_active else "inactive"
        source_topic = "*" if route.source_topic_id is None else route.source_topic_id
        destination_topic = (
            "*" if route.destination_topic_id is None else route.destination_topic_id
        )
        lines.append(
            f"#{route.id} | {route.source_chat_id}[topic:{source_topic}] "
            f"-> {route.destination_chat_id}[topic:{destination_topic}] | {status} | "
            f"created_by:{route.created_by_user_id}"
        )
    await message.answer("\n".join(lines))


@router.message(F.text, F.text.startswith("/remove_route"))
async def remove_route_handler(message: Message) -> None:
    if message.from_user is None:
        return

    caller_id = message.from_user.id
    is_owner = _is_owner(message)
    is_manager = await _is_manager(message)
    if not is_owner and not is_manager:
        await message.answer("You are not allowed to remove routes.")
        return

    route_id = _parse_one_int(message.text or "")
    if route_id is None:
        await message.answer("Usage: /remove_route &lt;route_id&gt;")
        return

    result = await remove_route_for_user(settings.db_path, route_id, caller_id, is_owner)
    if result == "not_found":
        await message.answer(f"Route #{route_id} was not found.")
        return
    if result == "forbidden":
        await message.answer(
            "You can remove only routes you created. Owner can remove any route."
        )
        return

    await message.answer(f"Route #{route_id} removed.")


@router.message(F.text == "/remove_all_routes")
async def remove_all_routes_handler(message: Message) -> None:
    if not _is_owner(message):
        await message.answer("Only owner can remove all routes.")
        return

    removed_count = await remove_all_routes(settings.db_path)
    await message.answer(f"Removed {removed_count} route(s).")
