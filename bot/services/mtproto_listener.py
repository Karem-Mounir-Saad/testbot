import asyncio

from aiogram import Bot
from loguru import logger

from bot.config import Settings
from bot.services.forwarder import delete_copies_for_source_message


async def run_mtproto_delete_listener(bot: Bot, settings: Settings) -> None:
    if settings.telethon_api_id is None or settings.telethon_api_hash is None:
        logger.info("MTProto delete listener is disabled (TELETHON_API_ID/API_HASH not set)")
        return

    try:
        from telethon import TelegramClient, events
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "MTProto listener is disabled because Telethon is not available: {}. "
            "Install it with 'python -m pip install Telethon==1.42.0' to enable this feature.",
            exc,
        )
        return

    client = TelegramClient(
        settings.telethon_session,
        settings.telethon_api_id,
        settings.telethon_api_hash,
    )
    watch_chat_ids = set(settings.telethon_watch_chat_ids)

    @client.on(events.MessageDeleted())
    async def on_message_deleted(event: events.MessageDeleted.Event) -> None:
        source_chat_id = getattr(event, "chat_id", None)
        if source_chat_id is None:
            logger.debug("Received MessageDeleted without chat_id; skipping")
            return

        source_chat_id = int(source_chat_id)
        if watch_chat_ids and source_chat_id not in watch_chat_ids:
            return

        deleted_ids = [int(x) for x in (event.deleted_ids or [])]
        if not deleted_ids:
            return

        logger.info(
            "MTProto delete event: source_chat_id={} deleted_ids={}",
            source_chat_id,
            deleted_ids,
        )

        for source_message_id in deleted_ids:
            await delete_copies_for_source_message(
                bot=bot,
                db_path=settings.db_path,
                source_chat_id=source_chat_id,
                source_message_id=source_message_id,
            )

    try:
        await client.start()
        logger.info(
            "MTProto listener started (session='{}', watch_filter_size={})",
            settings.telethon_session,
            len(watch_chat_ids),
        )
        await client.run_until_disconnected()
    except asyncio.CancelledError:
        logger.info("MTProto listener cancellation requested")
        raise
    finally:
        await client.disconnect()
