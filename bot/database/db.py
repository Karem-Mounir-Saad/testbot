from dataclasses import dataclass
from typing import Literal

import aiosqlite


@dataclass(frozen=True)
class Route:
    id: int
    source_chat_id: int
    destination_chat_id: int
    source_topic_id: int | None
    destination_topic_id: int | None
    created_by_user_id: int | None
    is_active: bool
    last_forwarded_signature: str | None


@dataclass(frozen=True)
class MessageLink:
    route_id: int
    source_chat_id: int
    source_message_id: int
    destination_chat_id: int
    destination_message_id: int


def _normalize_topic_id(value: int | None) -> int | None:
    # Backward compatibility: older data/commands sometimes stored 0 for "no topic".
    if value in (None, 0):
        return None
    return int(value)


CREATE_TABLES_SQL = [
    """
    CREATE TABLE IF NOT EXISTS routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_chat_id INTEGER NOT NULL,
        destination_chat_id INTEGER NOT NULL,
        source_topic_id INTEGER,
        destination_topic_id INTEGER,
        created_by_user_id INTEGER NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1,
        last_forwarded_signature TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(source_chat_id, destination_chat_id, source_topic_id, destination_topic_id)
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
    """
    CREATE TABLE IF NOT EXISTS route_managers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL UNIQUE,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """,
    "CREATE INDEX IF NOT EXISTS idx_routes_source_active ON routes(source_chat_id, is_active);",
    "CREATE INDEX IF NOT EXISTS idx_cache_chat_id ON message_cache(chat_id);",
    "CREATE INDEX IF NOT EXISTS idx_links_source_message ON message_links(source_chat_id, source_message_id);",
    "CREATE INDEX IF NOT EXISTS idx_route_managers_user_active ON route_managers(user_id, is_active);",
]


async def _migrate_routes_table_unique_constraint(
    db: aiosqlite.Connection,
    owner_id: int | None,
) -> None:
    row = await (
        await db.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'routes'"
        )
    ).fetchone()
    if row is None or row[0] is None:
        return

    create_sql = str(row[0])
    if "UNIQUE(source_chat_id, destination_chat_id)" not in create_sql:
        return

    owner_fallback = 0 if owner_id is None else int(owner_id)

    await db.execute(
        """
        CREATE TABLE routes_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_chat_id INTEGER NOT NULL,
            destination_chat_id INTEGER NOT NULL,
            source_topic_id INTEGER,
            destination_topic_id INTEGER,
            created_by_user_id INTEGER NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            last_forwarded_signature TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_chat_id, destination_chat_id, source_topic_id, destination_topic_id)
        )
        """
    )

    await db.execute(
        """
        INSERT INTO routes_new (
            id,
            source_chat_id,
            destination_chat_id,
            source_topic_id,
            destination_topic_id,
            created_by_user_id,
            is_active,
            last_forwarded_signature,
            created_at
        )
        SELECT
            id,
            source_chat_id,
            destination_chat_id,
            CASE
                WHEN source_topic_id IS NULL OR source_topic_id = 0 THEN NULL
                ELSE source_topic_id
            END,
            CASE
                WHEN destination_topic_id IS NULL OR destination_topic_id = 0 THEN NULL
                ELSE destination_topic_id
            END,
            COALESCE(created_by_user_id, ?),
            is_active,
            last_forwarded_signature,
            created_at
        FROM routes
        """,
        (owner_fallback,),
    )

    await db.execute("DROP TABLE routes")
    await db.execute("ALTER TABLE routes_new RENAME TO routes")
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_routes_source_active ON routes(source_chat_id, is_active)"
    )


async def _ensure_routes_topic_columns(db: aiosqlite.Connection) -> None:
    rows = await (await db.execute("PRAGMA table_info(routes)")).fetchall()
    columns = {str(row[1]) for row in rows}

    if "source_topic_id" not in columns:
        await db.execute("ALTER TABLE routes ADD COLUMN source_topic_id INTEGER")
    if "destination_topic_id" not in columns:
        await db.execute("ALTER TABLE routes ADD COLUMN destination_topic_id INTEGER")

    # Backward compatibility: normalize legacy "0 means no topic" rows.
    await db.execute("UPDATE routes SET source_topic_id = NULL WHERE source_topic_id = 0")
    await db.execute(
        "UPDATE routes SET destination_topic_id = NULL WHERE destination_topic_id = 0"
    )


async def _ensure_routes_created_by_column(
    db: aiosqlite.Connection,
    owner_id: int | None,
) -> None:
    rows = await (await db.execute("PRAGMA table_info(routes)")).fetchall()
    columns = {str(row[1]) for row in rows}

    if "created_by_user_id" not in columns:
        await db.execute("ALTER TABLE routes ADD COLUMN created_by_user_id INTEGER")

    if owner_id is not None:
        await db.execute(
            "UPDATE routes SET created_by_user_id = ? WHERE created_by_user_id IS NULL",
            (owner_id,),
        )


async def init_db(db_path: str, owner_id: int | None = None) -> None:
    async with aiosqlite.connect(db_path) as db:
        for statement in CREATE_TABLES_SQL:
            await db.execute(statement)
        await _migrate_routes_table_unique_constraint(db, owner_id)
        await _ensure_routes_topic_columns(db)
        await _ensure_routes_created_by_column(db, owner_id)
        await db.commit()


def _route_from_row(row: tuple) -> Route:
    return Route(
        id=int(row[0]),
        source_chat_id=int(row[1]),
        destination_chat_id=int(row[2]),
        source_topic_id=_normalize_topic_id(
            None if row[3] is None else int(row[3])
        ),
        destination_topic_id=_normalize_topic_id(
            None if row[4] is None else int(row[4])
        ),
        created_by_user_id=None if row[5] is None else int(row[5]),
        is_active=bool(row[6]),
        last_forwarded_signature=row[7],
    )


async def add_route(
    db_path: str,
    source_chat_id: int,
    destination_chat_id: int,
    source_topic_id: int | None = None,
    destination_topic_id: int | None = None,
    created_by_user_id: int | None = None,
) -> int:
    if created_by_user_id is None:
        raise ValueError("created_by_user_id is required")

    source_topic_id = _normalize_topic_id(source_topic_id)
    destination_topic_id = _normalize_topic_id(destination_topic_id)

    async with aiosqlite.connect(db_path) as db:
        existing = await (
            await db.execute(
                """
                SELECT id FROM routes
                WHERE source_chat_id = ?
                  AND destination_chat_id = ?
                  AND (
                    ((source_topic_id IS NULL OR source_topic_id = 0) AND ? IS NULL)
                    OR source_topic_id = ?
                  )
                  AND (
                    ((destination_topic_id IS NULL OR destination_topic_id = 0) AND ? IS NULL)
                    OR destination_topic_id = ?
                  )
                LIMIT 1
                """,
                (
                    source_chat_id,
                    destination_chat_id,
                    source_topic_id,
                    source_topic_id,
                    destination_topic_id,
                    destination_topic_id,
                ),
            )
        ).fetchone()

        if existing is not None:
            route_id = int(existing[0])
            await db.execute(
                """
                UPDATE routes
                SET is_active = 1,
                    source_topic_id = ?,
                    destination_topic_id = ?,
                    created_by_user_id = ?
                WHERE id = ?
                """,
                (source_topic_id, destination_topic_id, created_by_user_id, route_id),
            )
            await db.commit()
            return route_id

        cursor = await db.execute(
            """
            INSERT INTO routes (
                source_chat_id,
                destination_chat_id,
                source_topic_id,
                destination_topic_id,
                created_by_user_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                source_chat_id,
                destination_chat_id,
                source_topic_id,
                destination_topic_id,
                created_by_user_id,
            ),
        )
        await db.commit()
        return int(cursor.lastrowid)


async def add_route_for_user(
    db_path: str,
    source_chat_id: int,
    destination_chat_id: int,
    source_topic_id: int | None,
    destination_topic_id: int | None,
    created_by_user_id: int,
    is_owner: bool,
) -> tuple[Literal["created", "forbidden"], int]:
    source_topic_id = _normalize_topic_id(source_topic_id)
    destination_topic_id = _normalize_topic_id(destination_topic_id)

    async with aiosqlite.connect(db_path) as db:
        existing_row = await (
            await db.execute(
                """
                SELECT id, created_by_user_id
                FROM routes
                WHERE source_chat_id = ?
                  AND destination_chat_id = ?
                  AND (
                    ((source_topic_id IS NULL OR source_topic_id = 0) AND ? IS NULL)
                    OR source_topic_id = ?
                  )
                  AND (
                    ((destination_topic_id IS NULL OR destination_topic_id = 0) AND ? IS NULL)
                    OR destination_topic_id = ?
                  )
                LIMIT 1
                """,
                (
                    source_chat_id,
                    destination_chat_id,
                    source_topic_id,
                    source_topic_id,
                    destination_topic_id,
                    destination_topic_id,
                ),
            )
        ).fetchone()

        if existing_row is not None:
            route_id = int(existing_row[0])
            existing_creator = (
                None if existing_row[1] is None else int(existing_row[1])
            )
            if not is_owner and existing_creator != created_by_user_id:
                return "forbidden", route_id

            await db.execute(
                """
                UPDATE routes
                SET is_active = 1,
                    source_topic_id = ?,
                    destination_topic_id = ?,
                    created_by_user_id = ?
                WHERE id = ?
                """,
                (
                    source_topic_id,
                    destination_topic_id,
                    created_by_user_id,
                    route_id,
                ),
            )
            await db.commit()
            return "created", route_id

    route_id = await add_route(
        db_path=db_path,
        source_chat_id=source_chat_id,
        destination_chat_id=destination_chat_id,
        source_topic_id=source_topic_id,
        destination_topic_id=destination_topic_id,
        created_by_user_id=created_by_user_id,
    )
    return "created", route_id


async def list_routes(db_path: str) -> list[Route]:
    async with aiosqlite.connect(db_path) as db:
        rows = await (
            await db.execute(
                """
                SELECT
                    id,
                    source_chat_id,
                    destination_chat_id,
                    source_topic_id,
                    destination_topic_id,
                    created_by_user_id,
                    is_active,
                    last_forwarded_signature
                FROM routes
                ORDER BY id ASC
                """
            )
        ).fetchall()
    return [_route_from_row(row) for row in rows]


async def list_routes_for_user(
    db_path: str,
    user_id: int,
    is_owner: bool,
) -> list[Route]:
    async with aiosqlite.connect(db_path) as db:
        if is_owner:
            rows = await (
                await db.execute(
                    """
                    SELECT
                        id,
                        source_chat_id,
                        destination_chat_id,
                        source_topic_id,
                        destination_topic_id,
                        created_by_user_id,
                        is_active,
                        last_forwarded_signature
                    FROM routes
                    ORDER BY id ASC
                    """
                )
            ).fetchall()
        else:
            rows = await (
                await db.execute(
                    """
                    SELECT
                        id,
                        source_chat_id,
                        destination_chat_id,
                        source_topic_id,
                        destination_topic_id,
                        created_by_user_id,
                        is_active,
                        last_forwarded_signature
                    FROM routes
                    WHERE created_by_user_id = ?
                    ORDER BY id ASC
                    """,
                    (user_id,),
                )
            ).fetchall()
    return [_route_from_row(row) for row in rows]


async def remove_route(db_path: str, route_id: int) -> bool:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("DELETE FROM routes WHERE id = ?", (route_id,))
        await db.commit()
        return cursor.rowcount > 0


async def remove_route_for_user(
    db_path: str,
    route_id: int,
    user_id: int,
    is_owner: bool,
) -> Literal["deleted", "not_found", "forbidden"]:
    async with aiosqlite.connect(db_path) as db:
        row = await (
            await db.execute(
                "SELECT created_by_user_id FROM routes WHERE id = ?",
                (route_id,),
            )
        ).fetchone()

        if row is None:
            return "not_found"

        created_by_user_id = None if row[0] is None else int(row[0])
        if not is_owner and created_by_user_id != user_id:
            return "forbidden"

        await db.execute("DELETE FROM routes WHERE id = ?", (route_id,))
        await db.commit()
        return "deleted"


async def remove_all_routes(db_path: str) -> int:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute("DELETE FROM routes")
        await db.commit()
        return int(cursor.rowcount)


async def sync_route_managers_from_env(
    db_path: str,
    manager_user_ids: tuple[int, ...],
) -> None:
    normalized = {int(user_id) for user_id in manager_user_ids}

    async with aiosqlite.connect(db_path) as db:
        for user_id in normalized:
            await db.execute(
                """
                INSERT INTO route_managers (user_id, is_active)
                VALUES (?, 1)
                ON CONFLICT(user_id) DO UPDATE SET is_active = 1
                """,
                (user_id,),
            )

        if normalized:
            placeholders = ",".join("?" for _ in normalized)
            await db.execute(
                f"UPDATE route_managers SET is_active = 0 WHERE user_id NOT IN ({placeholders})",
                tuple(normalized),
            )
        else:
            await db.execute("UPDATE route_managers SET is_active = 0")

        await db.commit()


async def is_route_manager(db_path: str, user_id: int) -> bool:
    async with aiosqlite.connect(db_path) as db:
        row = await (
            await db.execute(
                """
                SELECT 1
                FROM route_managers
                WHERE user_id = ?
                  AND is_active = 1
                LIMIT 1
                """,
                (user_id,),
            )
        ).fetchone()

    return row is not None


async def get_active_routes_by_source(
    db_path: str,
    source_chat_id: int,
    source_topic_id: int | None,
) -> list[Route]:
    async with aiosqlite.connect(db_path) as db:
        rows = await (
            await db.execute(
                """
                SELECT
                    id,
                    source_chat_id,
                    destination_chat_id,
                    source_topic_id,
                    destination_topic_id,
                    created_by_user_id,
                    is_active,
                    last_forwarded_signature
                FROM routes
                WHERE source_chat_id = ?
                  AND is_active = 1
                  AND (
                    source_topic_id IS NULL
                    OR source_topic_id = 0
                    OR source_topic_id = ?
                  )
                ORDER BY id ASC
                """,
                (source_chat_id, source_topic_id),
            )
        ).fetchall()
    return [_route_from_row(row) for row in rows]


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


async def get_message_links_by_source_message(
    db_path: str,
    source_chat_id: int,
    source_message_id: int,
) -> list[MessageLink]:
    async with aiosqlite.connect(db_path) as db:
        rows = await (
            await db.execute(
                """
                SELECT
                    route_id,
                    source_chat_id,
                    source_message_id,
                    destination_chat_id,
                    destination_message_id
                FROM message_links
                WHERE source_chat_id = ?
                  AND source_message_id = ?
                """,
                (source_chat_id, source_message_id),
            )
        ).fetchall()

    return [
        MessageLink(
            route_id=int(row[0]),
            source_chat_id=int(row[1]),
            source_message_id=int(row[2]),
            destination_chat_id=int(row[3]),
            destination_message_id=int(row[4]),
        )
        for row in rows
    ]


async def delete_message_links_by_source_message(
    db_path: str,
    source_chat_id: int,
    source_message_id: int,
) -> int:
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            """
            DELETE FROM message_links
            WHERE source_chat_id = ?
              AND source_message_id = ?
            """,
            (source_chat_id, source_message_id),
        )
        await db.commit()
        return int(cursor.rowcount)
