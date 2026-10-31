from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timezone
import os
import sqlite3

# La BD se guarda en data/sandrone.db en la raiz del proyecto
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sandrone.db")


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    try:
        with connection:
            yield connection
    finally:
        connection.close()

def init_db():
    """Crea el esquema y los índices si todavía no existen."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS marriages (
                user1_id INTEGER NOT NULL,
                user2_id INTEGER NOT NULL,
                guild_id  INTEGER NOT NULL,
                date      TEXT    NOT NULL,
                PRIMARY KEY (user1_id, guild_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS config (
                guild_id INTEGER NOT NULL,
                key      TEXT    NOT NULL,
                value    TEXT    NOT NULL,
                PRIMARY KEY (guild_id, key)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS temp_channels (
                channel_id INTEGER PRIMARY KEY,
                guild_id   INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS strikes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id    INTEGER NOT NULL,
                user_id     INTEGER NOT NULL,
                moderator_id INTEGER,
                reason      TEXT NOT NULL,
                source      TEXT NOT NULL CHECK (source IN ('manual', 'spam')),
                created_at  TEXT NOT NULL,
                removed_by  INTEGER,
                removed_at  TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_strikes_active_user
            ON strikes (guild_id, user_id, removed_at)
        """)

# ── Marriages ────────────────────────────────────────────────────────────────

def get_partner(user_id: int, guild_id: int) -> int | None:
    """Devuelve el ID de la pareja del usuario, o None si no está casado."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT user2_id FROM marriages WHERE user1_id = ? AND guild_id = ?",
            (user_id, guild_id)
        ).fetchone()
        if row:
            return row[0]
        row = conn.execute(
            "SELECT user1_id FROM marriages WHERE user2_id = ? AND guild_id = ?",
            (user_id, guild_id)
        ).fetchone()
        return row[0] if row else None

def add_marriage(user1_id: int, user2_id: int, guild_id: int, date: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO marriages (user1_id, user2_id, guild_id, date) VALUES (?, ?, ?, ?)",
            (user1_id, user2_id, guild_id, date)
        )

def remove_marriage(user_id: int, guild_id: int):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM marriages WHERE (user1_id = ? OR user2_id = ?) AND guild_id = ?",
            (user_id, user_id, guild_id)
        )

# ── Config ────────────────────────────────────────────────────────────────────

def get_config(guild_id: int, key: str) -> str | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM config WHERE guild_id = ? AND key = ?",
            (guild_id, key)
        ).fetchone()
        return row[0] if row else None

def set_config(guild_id: int, key: str, value: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO config (guild_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(guild_id, key) DO UPDATE SET value = excluded.value",
            (guild_id, key, value)
        )

# ── Canales temporales ────────────────────────────────────────────────────────

def add_temp_channel(channel_id: int, guild_id: int):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO temp_channels (channel_id, guild_id) VALUES (?, ?)",
            (channel_id, guild_id)
        )

def remove_temp_channel(channel_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM temp_channels WHERE channel_id = ?", (channel_id,))

def get_temp_channels(guild_id: int) -> list[int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT channel_id FROM temp_channels WHERE guild_id = ?", (guild_id,)
        ).fetchall()
        return [r[0] for r in rows]

# ── Strikes ───────────────────────────────────────────────────────────────────

def add_strike(
    guild_id: int,
    user_id: int,
    moderator_id: int | None,
    reason: str,
    source: str,
) -> int:
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO strikes (guild_id, user_id, moderator_id, reason, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, moderator_id, reason, source, created_at),
        )
        return cursor.lastrowid

def get_strike_count(guild_id: int, user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM strikes WHERE guild_id = ? AND user_id = ? AND removed_at IS NULL",
            (guild_id, user_id),
        ).fetchone()
        return row[0]

def get_strike_history(
    guild_id: int,
    user_id: int,
    limit: int = 5,
) -> list[tuple[str, str, str]]:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT reason, created_at, source
            FROM strikes
            WHERE guild_id = ? AND user_id = ? AND removed_at IS NULL
            ORDER BY id DESC
            LIMIT ?
            """,
            (guild_id, user_id, limit),
        ).fetchall()

def get_strike_user_count(guild_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT COUNT(DISTINCT user_id)
            FROM strikes
            WHERE guild_id = ? AND removed_at IS NULL
            """,
            (guild_id,),
        ).fetchone()
        return row[0]

def get_strike_total(guild_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM strikes WHERE guild_id = ? AND removed_at IS NULL",
            (guild_id,),
        ).fetchone()
        return row[0]

def get_strike_overview(
    guild_id: int,
    limit: int,
    offset: int,
) -> list[tuple[int, int]]:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT user_id, COUNT(*) AS strike_count
            FROM strikes
            WHERE guild_id = ? AND removed_at IS NULL
            GROUP BY user_id
            ORDER BY strike_count DESC, user_id
            LIMIT ? OFFSET ?
            """,
            (guild_id, limit, offset),
        ).fetchall()

def remove_latest_strike(guild_id: int, user_id: int, moderator_id: int) -> bool:
    """Retira el último strike activo sin borrar su registro de auditoría."""
    removed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE strikes
            SET removed_by = ?, removed_at = ?
            WHERE id = (
                SELECT id
                FROM strikes
                WHERE guild_id = ? AND user_id = ? AND removed_at IS NULL
                ORDER BY id DESC
                LIMIT 1
            )
            """,
            (moderator_id, removed_at, guild_id, user_id),
        )
        return cursor.rowcount > 0
