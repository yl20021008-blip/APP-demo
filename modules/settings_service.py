from __future__ import annotations

try:
    import streamlit as st
except Exception:  # noqa: BLE001
    st = None

from sqlalchemy import insert, select, update

from modules.database import app_settings, get_connection, init_database


def _query_setting(key: str, default: str) -> str:
    init_database()
    with get_connection() as conn:
        row = conn.execute(
            select(app_settings.c.setting_value).where(app_settings.c.setting_key == key)
        ).first()
    return str(row[0]) if row else default


if st is not None:
    @st.cache_data(ttl=300, show_spinner=False)
    def _cached_setting(key: str, default: str) -> str:
        return _query_setting(key, default)
else:
    def _cached_setting(key: str, default: str) -> str:
        return _query_setting(key, default)


def get_setting(key: str, default: str) -> str:
    return _cached_setting(key, default)


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
    try:
        _cached_setting.clear()
    except Exception:
        pass
