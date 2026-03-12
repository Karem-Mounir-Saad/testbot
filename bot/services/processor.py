from typing import Final


QUESTION_ANSWERS: Final[dict[str, str]] = {
    "how are you": "I am doing great, thanks for asking! 😊",
    "how old are you": "I am a bot, so I do not have a real age 🤖",
    "where are you from": "I live in the cloud and run on your server ☁️",
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
