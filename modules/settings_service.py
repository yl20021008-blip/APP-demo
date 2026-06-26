from __future__ import annotations

from modules.database import get_connection


def get_setting(key: str, default: str) -> str:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT setting_value
            FROM app_settings
            WHERE setting_key = ?
            """,
            (key,),
        ).fetchone()

    return str(row["setting_value"]) if row else default


def set_setting(key: str, value: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO app_settings(setting_key, setting_value)
            VALUES (?, ?)
            ON CONFLICT(setting_key)
            DO UPDATE SET setting_value = excluded.setting_value
            """,
            (key, str(value)),
        )
