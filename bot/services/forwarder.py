from aiogram import Bot
from aiogram.types import (
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
)
from loguru import logger

from bot.database.db import (
    MessageLink,
    Route,
    cache_message,
    get_message_link,
    get_active_routes_by_source,
    insert_forward_log,
    trim_cache,
    upsert_message_link,
    update_route_last_forwarded_signature,
)


async def _forward_for_route(
    bot: Bot,
    db_path: str,
    route: Route,
    source_message_id: int,
) -> None:
    signature = str(source_message_id)
    if route.last_forwarded_signature == signature:
        return

    try:
        copied = await bot.copy_message(
            chat_id=route.destination_chat_id,
            from_chat_id=route.source_chat_id,
            message_id=source_message_id,
        )

        await upsert_message_link(
            db_path=db_path,
            route_id=route.id,
            source_chat_id=route.source_chat_id,
            source_message_id=source_message_id,
            destination_chat_id=route.destination_chat_id,
            destination_message_id=int(copied.message_id),
        )

        await update_route_last_forwarded_signature(db_path, route.id, signature)
        await insert_forward_log(
            db_path=db_path,
            route_id=route.id,
            source_chat_id=route.source_chat_id,
            destination_chat_id=route.destination_chat_id,
            message_ids=[source_message_id],
            status="success",
        )
        logger.info(
            "Copied source message {} from {} to {} (route #{})",
            source_message_id,
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
            message_ids=[source_message_id],
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
    logger.info(
        "Copying incoming message immediately for source_chat_id={} message_id={}",
        source_chat_id,
        message_id,
    )

    for route in routes:
        await _forward_for_route(
            bot=bot,
            db_path=db_path,
            route=route,
            source_message_id=message_id,
        )


async def _replace_destination_copy_for_edit(
    bot: Bot,
    db_path: str,
    route: Route,
    link: MessageLink,
    source_message_id: int,
) -> None:
    try:
        try:
            await bot.delete_message(
                chat_id=link.destination_chat_id,
                message_id=link.destination_message_id,
            )
            logger.info(
                "Deleted old destination message {} in chat {} for route #{} before edit sync",
                link.destination_message_id,
                link.destination_chat_id,
                route.id,
            )
        except Exception as delete_exc:  # noqa: BLE001
            logger.warning(
                "Could not delete old destination message {} in chat {} for route #{}: {}",
                link.destination_message_id,
                link.destination_chat_id,
                route.id,
                delete_exc,
            )

        copied = await bot.copy_message(
            chat_id=route.destination_chat_id,
            from_chat_id=route.source_chat_id,
            message_id=source_message_id,
        )

        await upsert_message_link(
            db_path=db_path,
            route_id=route.id,
            source_chat_id=route.source_chat_id,
            source_message_id=source_message_id,
            destination_chat_id=route.destination_chat_id,
            destination_message_id=int(copied.message_id),
        )

        await update_route_last_forwarded_signature(db_path, route.id, str(source_message_id))

        await insert_forward_log(
            db_path=db_path,
            route_id=route.id,
            source_chat_id=route.source_chat_id,
            destination_chat_id=route.destination_chat_id,
            message_ids=[source_message_id],
            status="success",
        )

        logger.info(
            "Synced edited source message {} to destination {} (route #{})",
            source_message_id,
            route.destination_chat_id,
            route.id,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Failed syncing edited message {} for route #{} ({} -> {})",
            source_message_id,
            route.id,
            route.source_chat_id,
            route.destination_chat_id,
        )
        await insert_forward_log(
            db_path=db_path,
            route_id=route.id,
            source_chat_id=route.source_chat_id,
            destination_chat_id=route.destination_chat_id,
            message_ids=[source_message_id],
            status="failed",
            error=str(exc),
        )


async def _try_inline_edit_for_link(
    bot: Bot,
    link: MessageLink,
    source_message: Message,
) -> bool:
    media = None
    if source_message.photo:
        media = InputMediaPhoto(
            media=source_message.photo[-1].file_id,
            caption=source_message.caption,
            caption_entities=source_message.caption_entities,
        )
    elif source_message.video:
        media = InputMediaVideo(
            media=source_message.video.file_id,
            caption=source_message.caption,
            caption_entities=source_message.caption_entities,
        )
    elif source_message.animation:
        media = InputMediaAnimation(
            media=source_message.animation.file_id,
            caption=source_message.caption,
            caption_entities=source_message.caption_entities,
        )
    elif source_message.document:
        media = InputMediaDocument(
            media=source_message.document.file_id,
            caption=source_message.caption,
            caption_entities=source_message.caption_entities,
        )
    elif source_message.audio:
        media = InputMediaAudio(
            media=source_message.audio.file_id,
            caption=source_message.caption,
            caption_entities=source_message.caption_entities,
        )

    try:
        if media is not None:
            await bot.edit_message_media(
                chat_id=link.destination_chat_id,
                message_id=link.destination_message_id,
                media=media,
            )
            return True

        if source_message.text is not None:
            await bot.edit_message_text(
                chat_id=link.destination_chat_id,
                message_id=link.destination_message_id,
                text=source_message.text,
                entities=source_message.entities,
            )
            return True

        if source_message.caption is not None:
            await bot.edit_message_caption(
                chat_id=link.destination_chat_id,
                message_id=link.destination_message_id,
                caption=source_message.caption,
                caption_entities=source_message.caption_entities,
            )
            return True

        return False
    except Exception as exc:  # noqa: BLE001
        if "message is not modified" in str(exc).lower():
            return True
        logger.warning(
            "Inline edit failed for destination message {} in chat {}: {}",
            link.destination_message_id,
            link.destination_chat_id,
            exc,
        )
        return False


async def sync_edited_source_message(
    bot: Bot,
    db_path: str,
    source_message: Message,
) -> None:
    if source_message.chat is None or source_message.message_id is None:
        return

    source_chat_id = source_message.chat.id
    source_message_id = source_message.message_id

    logger.info(
        "Processing edited source message: source_chat_id={} message_id={}",
        source_chat_id,
        source_message_id,
    )

    routes = await get_active_routes_by_source(db_path, source_chat_id)
    if not routes:
        logger.info("No active routes for edited source_chat_id={}", source_chat_id)
        return

    for route in routes:
        link = await get_message_link(
            db_path=db_path,
            route_id=route.id,
            source_chat_id=source_chat_id,
            source_message_id=source_message_id,
        )
        if link is None:
            logger.info(
                "No mapping found for edited message {} on route #{}; skipping",
                source_message_id,
                route.id,
            )
            continue

        edited_inline = await _try_inline_edit_for_link(
            bot=bot,
            link=link,
            source_message=source_message,
        )
        if edited_inline:
            await insert_forward_log(
                db_path=db_path,
                route_id=route.id,
                source_chat_id=route.source_chat_id,
                destination_chat_id=route.destination_chat_id,
                message_ids=[source_message_id],
                status="success",
            )
            logger.info(
                "Inline-edited destination message {} for source message {} on route #{}",
                link.destination_message_id,
                source_message_id,
                route.id,
            )
            continue

        await _replace_destination_copy_for_edit(
            bot=bot,
            db_path=db_path,
            route=route,
            link=link,
            source_message_id=source_message_id,
        )







