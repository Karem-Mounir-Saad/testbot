from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.config import get_settings
from bot.database.db import save_qa
from bot.handlers.states import QAFlow
from bot.services.processor import resolve_answer, supported_questions_text

router = Router()
settings = get_settings()


@router.message(StateFilter(QAFlow.awaiting_button), F.text)
async def ask_questions_button_handler(message: Message, state: FSMContext) -> None:
    incoming = (message.text or "").strip().lower()
    if incoming != "ask questions":
        await message.answer("Please press the 'Ask Questions' button to continue.")
        return

    await state.set_state(QAFlow.awaiting_question)
    await message.answer(
        "Great! Ask one of these questions:\n"
        f"{supported_questions_text()}"
    )


@router.message(StateFilter(QAFlow.awaiting_question), F.text)
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


@router.message(F.text)
async def out_of_flow_handler(message: Message) -> None:
    await message.answer("Please use /start first, then press 'Ask Questions'.")
