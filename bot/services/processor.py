from typing import Final


QUESTION_ANSWERS: Final[dict[str, str]] = {
    "how are you": "I am doing great, thanks for asking! 😊",
    "how old are you": "I am a bot, so I do not have a real age 🤖",
    "where are you from": "I live in the cloud and run on your server ☁️",
}

QUESTION_CALLBACKS: Final[dict[str, str]] = {
    "how_are_you": "how are you",
    "how_old_are_you": "how old are you",
    "where_are_you_from": "where are you from",
}


def normalize_text(text: str) -> str:
    cleaned = text.strip().lower()
    for ch in ("?", "!", ".", ","):
        cleaned = cleaned.replace(ch, "")
    return " ".join(cleaned.split())


def resolve_answer(message_text: str) -> tuple[str, str] | None:
    normalized = normalize_text(message_text)
    answer = QUESTION_ANSWERS.get(normalized)
    if answer is None:
        return None
    return normalized, answer


def supported_questions_text() -> str:
    return "\n".join(f"- {q}" for q in QUESTION_ANSWERS)


def resolve_callback_answer(callback_key: str) -> tuple[str, str] | None:
    question = QUESTION_CALLBACKS.get(callback_key)
    if question is None:
        return None
    answer = QUESTION_ANSWERS.get(question)
    if answer is None:
        return None
    return question, answer
