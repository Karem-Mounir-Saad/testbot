from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup

from bot.handlers.states import QAFlow

router = Router()


def _ask_questions_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Ask Questions")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


@router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    name = message.from_user.full_name if message.from_user else "there"
    await state.set_state(QAFlow.awaiting_button)
    await message.answer(
        f"Hello, {name}! 👋\n"
        "Press the button below to start asking questions.",
        reply_markup=_ask_questions_keyboard(),
    )
