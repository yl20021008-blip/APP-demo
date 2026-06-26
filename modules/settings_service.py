from __future__ import annotations

from sqlalchemy import insert, select, update

from modules.database import app_settings, get_connection, init_database


def get_setting(key: str, default: str) -> str:
    init_database()
    with get_connection() as conn:
        row = conn.execute(
            select(app_settings.c.setting_value).where(app_settings.c.setting_key == key)
        ).first()
    return str(row[0]) if row else default


def set_setting(key: str, value: str) -> None:
    init_database()
    with get_connection() as conn:
        row = conn.execute(
            select(app_settings.c.setting_key).where(app_settings.c.setting_key == key)
        ).first()
        if row:
            conn.execute(update(app_settings).where(app_settings.c.setting_key == key).values(setting_value=str(value)))
        else:
            conn.execute(insert(app_settings).values(setting_key=key, setting_value=str(value)))
