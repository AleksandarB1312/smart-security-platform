import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("GATEWAY_DB_PATH", Path(__file__).parent / "devices.db"))


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
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS auth_failures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            client_ip TEXT,
            occurred_at TEXT NOT NULL DEFAULT (datetime('now'))
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


def log_failed_attempt(device_id, client_ip):
    connection = get_connection()
    connection.execute(
        "INSERT INTO auth_failures (device_id, client_ip) VALUES (?, ?)",
        (device_id, client_ip),
    )
    connection.commit()
    connection.close()


def count_recent_failures(device_id, window_seconds):
    connection = get_connection()
    row = connection.execute(
        """
        SELECT COUNT(*) AS failure_count FROM auth_failures
        WHERE device_id = ?
        AND occurred_at >= datetime('now', ?)
        """,
        (device_id, f"-{window_seconds} seconds"),
    ).fetchone()
    connection.close()
    return row["failure_count"]


def list_recent_failures(limit=50):
    connection = get_connection()
    rows = connection.execute(
        "SELECT device_id, client_ip, occurred_at FROM auth_failures "
        "ORDER BY occurred_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    connection.close()
    return [dict(row) for row in rows]
