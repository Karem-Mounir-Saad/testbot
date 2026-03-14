from aiogram import Bot
from loguru import logger

from bot.database.db import (
    Route,
    cache_message,
    get_active_routes_by_source,
    insert_forward_log,
    trim_cache,
    update_route_last_forwarded_signature,
)


def _build_signature(message_ids: list[int]) -> str:
    return ":".join(str(message_id) for message_id in message_ids)


async def _forward_for_route(
    bot: Bot,
    db_path: str,
    route: Route,
    message_ids: list[int],
) -> None:
    signature = _build_signature(message_ids)
    if route.last_forwarded_signature == signature:
        return

    try:
        await bot.forward_messages(
            chat_id=route.destination_chat_id,
            from_chat_id=route.source_chat_id,
            message_ids=message_ids,
        )
        await update_route_last_forwarded_signature(db_path, route.id, signature)
        await insert_forward_log(
            db_path=db_path,
            route_id=route.id,
            source_chat_id=route.source_chat_id,
            destination_chat_id=route.destination_chat_id,
            message_ids=message_ids,
            status="success",
        )
        logger.info(
            "Forwarded {} messages from {} to {} (route #{})",
            len(message_ids),
            route.source_chat_id,
            route.destination_chat_id,
            route.id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed forwarding for route #{} ({} -> {})",
            route.id,
            route.source_chat_id,
            route.destination_chat_id,
        )
        await insert_forward_log(
            db_path=db_path,
            route_id=route.id,
            source_chat_id=route.source_chat_id,
            destination_chat_id=route.destination_chat_id,
            message_ids=message_ids,
            status="failed",
            error=str(exc),
        )


async def process_source_message(
    bot: Bot,
    db_path: str,
    source_chat_id: int,
    message_id: int,
) -> None:
    logger.info(
        "Processing source message: source_chat_id={} message_id={}",
        source_chat_id,
        message_id,
    )
    routes = await get_active_routes_by_source(db_path, source_chat_id)
    if not routes:
        logger.info("No active routes for source_chat_id={}", source_chat_id)
        return

    logger.info(
        "Found {} active route(s) for source_chat_id={}",
        len(routes),
        source_chat_id,
    )

    await cache_message(db_path, source_chat_id, message_id)
    await trim_cache(db_path, source_chat_id, keep_last=20)
    latest_ids = [message_id]
    logger.info(
        "Forwarding incoming message immediately for source_chat_id={}: {}",
        source_chat_id,
        latest_ids,
    )

    for route in routes:
        await _forward_for_route(bot=bot, db_path=db_path, route=route, message_ids=latest_ids)




