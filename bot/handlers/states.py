from aiogram.fsm.state import State, StatesGroup


class QAFlow(StatesGroup):
    awaiting_button = State()
    awaiting_question = State()
