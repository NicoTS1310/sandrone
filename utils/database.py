import sqlite3
import os

# La BD se guarda en data/sandrone.db en la raiz del proyecto
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "sandrone.db")

def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    """Crea las tablas si no existen. Se llama al iniciar cada cog que use la BD."""
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
        conn.commit()

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
        conn.commit()

def remove_marriage(user_id: int, guild_id: int):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM marriages WHERE (user1_id = ? OR user2_id = ?) AND guild_id = ?",
            (user_id, user_id, guild_id)
        )
        conn.commit()

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
        conn.commit()

# ── Canales temporales ────────────────────────────────────────────────────────

def add_temp_channel(channel_id: int, guild_id: int):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO temp_channels (channel_id, guild_id) VALUES (?, ?)",
            (channel_id, guild_id)
        )
        conn.commit()

def remove_temp_channel(channel_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM temp_channels WHERE channel_id = ?", (channel_id,))
        conn.commit()

def get_temp_channels(guild_id: int) -> list[int]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT channel_id FROM temp_channels WHERE guild_id = ?", (guild_id,)
        ).fetchall()
        return [r[0] for r in rows]
