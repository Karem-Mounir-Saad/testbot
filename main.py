import asyncio
import sys
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from loguru import logger

from bot.config import get_settings
from bot.database.db import init_db
from bot.handlers.commands import router as commands_router
from bot.handlers.messages import router as messages_router
from bot.services.mtproto_listener import run_mtproto_delete_listener


async def main() -> None:
    settings = get_settings()

    logger.remove()
    logger.add(sys.stdout, level=settings.log_level)

    await init_db(settings.db_path)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(commands_router)
    dp.include_router(messages_router)

    mtproto_task = asyncio.create_task(run_mtproto_delete_listener(bot, settings))

    logger.info("Bot is starting polling...")
    try:
        await dp.start_polling(bot)
    finally:
        if not mtproto_task.done():
            mtproto_task.cancel()
            with suppress(asyncio.CancelledError):
                await mtproto_task
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")
