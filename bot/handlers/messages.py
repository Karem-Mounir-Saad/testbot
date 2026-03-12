from aiogram import F, Router
from aiogram.types import Message

from bot.config import get_settings
from bot.database.db import save_qa
from bot.services.processor import resolve_answer, supported_questions_text

router = Router()
settings = get_settings()


@router.message(F.photo)
async def message_handler(message: Message) -> None:
    user_text = message.text or ""
    resolved = resolve_answer(user_text)

    if resolved is None:
        await message.answer(
            "I can only answer these questions:\n"
            f"{supported_questions_text()}"
        )
        return

    question, answer = resolved
    user = message.from_user
    username = user.username if user else None
    user_id = user.id if user else 0

    await message.answer(answer)
    await save_qa(
        db_path=settings.db_path,
        username=username,
        user_id=user_id,
        question=question,
        answer=answer,
    )
