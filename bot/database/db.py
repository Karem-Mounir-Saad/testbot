import aiosqlite


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS qa_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    user_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()

async def save_qa(
    db_path: str,
    username: str | None,
    user_id: int,
    question: str,
    answer: str,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO qa_logs (username, user_id, question, answer)
            VALUES (?, ?, ?, ?)
            """,
            (username, user_id, question, answer),
        )
        await db.commit()
