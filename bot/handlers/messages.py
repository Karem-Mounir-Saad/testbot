from aiogram import Router
from aiogram.types import Message
from loguru import logger

from bot.config import get_settings
from bot.services.forwarder import process_source_message

router = Router()
settings = get_settings()


@router.message()
async def listen_group_messages(message: Message) -> None:
    if message.chat is None or message.message_id is None:
        return
    logger.info(
        "Incoming message update: chat_id={} chat_type={} message_id={}",
        message.chat.id,
        message.chat.type,
        message.message_id,
    )
    await process_source_message(
        bot=message.bot,
        db_path=settings.db_path,
        source_chat_id=message.chat.id,
        message_id=message.message_id,
    )


@router.channel_post()
async def listen_channel_posts(message: Message) -> None:
    if message.chat is None or message.message_id is None:
        return
    logger.info(
        "Incoming channel_post update: chat_id={} chat_type={} message_id={}",
        message.chat.id,
        message.chat.type,
        message.message_id,
    )
    await process_source_message(
        bot=message.bot,
        db_path=settings.db_path,
        source_chat_id=message.chat.id,
        message_id=message.message_id,
    )
