from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot.config import get_settings
from bot.database.db import save_qa
from bot.handlers.states import QAFlow
from bot.services.processor import resolve_callback_answer

router = Router()
settings = get_settings()


def _questions_inline_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="How are you?", callback_data="q:how_are_you"),
                InlineKeyboardButton(
                    text="How old are you?", callback_data="q:how_old_are_you"
                ),
                InlineKeyboardButton(
                    text="Where are you from?", callback_data="q:where_are_you_from"
                ),
            ],
        ]
    )


@router.message(StateFilter(QAFlow.awaiting_button), F.text)
async def ask_questions_button_handler(message: Message, state: FSMContext) -> None:
    incoming = (message.text or "").strip().lower()
    if incoming != "ask questions":
        await message.answer("Please press the 'Ask Questions' button to continue.")
        return

    await state.set_state(QAFlow.awaiting_question)
    await message.answer(
        "Great! Please choose one question:",
        reply_markup=_questions_inline_keyboard(),
    )


@router.callback_query(StateFilter(QAFlow.awaiting_question), F.data.startswith("q:"))
async def question_callback_handler(callback: CallbackQuery) -> None:
    callback_data = callback.data or ""
    callback_key = callback_data.split("q:", maxsplit=1)[-1]
    resolved = resolve_callback_answer(callback_key)

    if resolved is None:
        await callback.answer("Invalid choice", show_alert=False)
        return

    question, answer = resolved
    user = callback.from_user
    username = user.username if user else None
    user_id = user.id if user else 0

    if callback.message:
        await callback.message.answer(answer)

    await save_qa(
        db_path=settings.db_path,
        username=username,
        user_id=user_id,
        question=question,
        answer=answer,
    )
    await callback.answer()


@router.message(StateFilter(QAFlow.awaiting_question), F.text)
async def text_in_question_state_handler(message: Message) -> None:
    await message.answer("Please choose a question from the inline buttons.")


@router.message(F.text)
async def out_of_flow_handler(message: Message) -> None:
    await message.answer("Please use /start first, then press 'Ask Questions'.")
