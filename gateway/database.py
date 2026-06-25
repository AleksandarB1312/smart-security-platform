import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "devices.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_connection()
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS devices (
            device_id TEXT PRIMARY KEY,
            public_key TEXT NOT NULL,
            registered_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    connection.commit()
    connection.close()


def register_device(device_id, public_key):
    connection = get_connection()
    connection.execute(
        "INSERT OR REPLACE INTO devices (device_id, public_key) VALUES (?, ?)",
        (device_id, str(public_key)),
    )
    connection.commit()
    connection.close()


def get_device_public_key(device_id):
    connection = get_connection()
    row = connection.execute(
        "SELECT public_key FROM devices WHERE device_id = ?", (device_id,)
    ).fetchone()
    connection.close()
    return int(row["public_key"]) if row else None


def list_devices():
    connection = get_connection()
    rows = connection.execute(
        "SELECT device_id, registered_at FROM devices"
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]
