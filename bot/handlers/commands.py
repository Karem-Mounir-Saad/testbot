from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.services.processor import supported_questions_text

router = Router()


@router.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    name = message.from_user.full_name if message.from_user else "there"
    await message.answer(
        f"Hello, {name}! 👋\n"
        "I can answer exactly these questions:\n"
        f"{supported_questions_text()}"
    )
