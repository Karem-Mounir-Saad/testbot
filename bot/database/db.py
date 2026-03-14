from dataclasses import dataclass

import aiosqlite


@dataclass(frozen=True)
class Route:
    id: int
    source_chat_id: int
    destination_chat_id: int
    is_active: bool
    last_forwarded_signature: str | None


@dataclass(frozen=True)
class MessageLink:
    route_id: int
    source_chat_id: int
    source_message_id: int
    destination_chat_id: int
    destination_message_id: int


CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_chat_id INTEGER NOT NULL,
        destination_chat_id INTEGER NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        last_forwarded_signature TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source_chat_id, destination_chat_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS message_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        message_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(chat_id, message_id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS forward_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_id INTEGER NOT NULL,
        source_chat_id INTEGER NOT NULL,
        destination_chat_id INTEGER NOT NULL,
        message_ids TEXT NOT NULL,
        status TEXT NOT NULL,
        error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS message_links (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_id INTEGER NOT NULL,
        source_chat_id INTEGER NOT NULL,
        source_message_id INTEGER NOT NULL,
        destination_chat_id INTEGER NOT NULL,
        destination_message_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(route_id, source_chat_id, source_message_id)
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_routes_source_active ON routes(source_chat_id, is_active);",
    "CREATE INDEX IF NOT EXISTS idx_cache_chat_id ON message_cache(chat_id);",
    "CREATE INDEX IF NOT EXISTS idx_links_source_message ON message_links(source_chat_id, source_message_id);",
]


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        for statement in CREATE_TABLES_SQL:
            await db.execute(statement)
        await db.commit()


async def add_route(db_path: str, source_chat_id: int, destination_chat_id: int) -> int:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            INSERT INTO routes (source_chat_id, destination_chat_id)
            VALUES (?, ?)
            ON CONFLICT(source_chat_id, destination_chat_id)
            DO UPDATE SET is_active = 1
            """,
            (source_chat_id, destination_chat_id),
        )
        await db.commit()
        if cursor.lastrowid:
            return int(cursor.lastrowid)

        row = await (
            await db.execute(
                """
                SELECT id FROM routes
                WHERE source_chat_id = ? AND destination_chat_id = ?
                """,
                (source_chat_id, destination_chat_id),
            )
        ).fetchone()
        return int(row[0])


async def list_routes(db_path: str) -> list[Route]:
    async with aiosqlite.connect(db_path) as db:
        rows = await (
            await db.execute(
                """
                SELECT id, source_chat_id, destination_chat_id, is_active, last_forwarded_signature
                FROM routes
                ORDER BY id ASC
                """
            )
        ).fetchall()
    return [
        Route(
            id=row[0],
            source_chat_id=row[1],
            destination_chat_id=row[2],
            is_active=bool(row[3]),
            last_forwarded_signature=row[4],
        )
        for row in rows
    ]


async def remove_route(db_path: str, route_id: int) -> bool:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("DELETE FROM routes WHERE id = ?", (route_id,))
        await db.commit()
        return cursor.rowcount > 0


async def get_active_routes_by_source(db_path: str, source_chat_id: int) -> list[Route]:
    async with aiosqlite.connect(db_path) as db:
        rows = await (
            await db.execute(
                """
                SELECT id, source_chat_id, destination_chat_id, is_active, last_forwarded_signature
                FROM routes
                WHERE source_chat_id = ? AND is_active = 1
                ORDER BY id ASC
                """,
                (source_chat_id,),
            )
        ).fetchall()
    return [
        Route(
            id=row[0],
            source_chat_id=row[1],
            destination_chat_id=row[2],
            is_active=bool(row[3]),
            last_forwarded_signature=row[4],
        )
        for row in rows
    ]


async def cache_message(db_path: str, chat_id: int, message_id: int) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT OR IGNORE INTO message_cache (chat_id, message_id)
            VALUES (?, ?)
            """,
            (chat_id, message_id),
        )
        await db.commit()


async def trim_cache(db_path: str, chat_id: int, keep_last: int = 20) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            DELETE FROM message_cache
            WHERE chat_id = ?
              AND id NOT IN (
                SELECT id FROM message_cache
                WHERE chat_id = ?
                ORDER BY message_id DESC
                LIMIT ?
              )
            """,
            (chat_id, chat_id, keep_last),
        )
        await db.commit()


async def get_latest_cached_message_ids(
    db_path: str,
    chat_id: int,
    limit: int = 2,
) -> list[int]:
    async with aiosqlite.connect(db_path) as db:
        rows = await (
            await db.execute(
                """
                SELECT message_id FROM message_cache
                WHERE chat_id = ?
                ORDER BY message_id DESC
                LIMIT ?
                """,
                (chat_id, limit),
            )
        ).fetchall()
    return sorted(int(row[0]) for row in rows)


async def update_route_last_forwarded_signature(
    db_path: str,
    route_id: int,
    signature: str,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE routes SET last_forwarded_signature = ? WHERE id = ?",
            (signature, route_id),
        )
        await db.commit()


async def insert_forward_log(
    db_path: str,
    route_id: int,
    source_chat_id: int,
    destination_chat_id: int,
    message_ids: list[int],
    status: str,
    error: str | None = None,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO forward_logs (
                route_id, source_chat_id, destination_chat_id,
                message_ids, status, error
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                route_id,
                source_chat_id,
                destination_chat_id,
                ",".join(str(x) for x in message_ids),
                status,
                error,
            ),
        )
        await db.commit()


async def upsert_message_link(
    db_path: str,
    route_id: int,
    source_chat_id: int,
    source_message_id: int,
    destination_chat_id: int,
    destination_message_id: int,
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO message_links (
                route_id,
                source_chat_id,
                source_message_id,
                destination_chat_id,
                destination_message_id,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(route_id, source_chat_id, source_message_id)
            DO UPDATE SET
                destination_chat_id = excluded.destination_chat_id,
                destination_message_id = excluded.destination_message_id,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                route_id,
                source_chat_id,
                source_message_id,
                destination_chat_id,
                destination_message_id,
            ),
        )
        await db.commit()


async def get_message_link(
    db_path: str,
    route_id: int,
    source_chat_id: int,
    source_message_id: int,
) -> MessageLink | None:
    async with aiosqlite.connect(db_path) as db:
        row = await (
            await db.execute(
                """
                SELECT
                    route_id,
                    source_chat_id,
                    source_message_id,
                    destination_chat_id,
                    destination_message_id
                FROM message_links
                WHERE route_id = ?
                  AND source_chat_id = ?
                  AND source_message_id = ?
                """,
                (route_id, source_chat_id, source_message_id),
            )
        ).fetchone()

    if row is None:
        return None

    return MessageLink(
        route_id=int(row[0]),
        source_chat_id=int(row[1]),
        source_message_id=int(row[2]),
        destination_chat_id=int(row[3]),
        destination_message_id=int(row[4]),
    )
