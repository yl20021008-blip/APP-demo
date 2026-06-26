from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy import insert, select

from modules.database import get_connection, init_database, users, ensure_user_word_status

PEPPER = 'ielts-vocabulary-app-v1.2'


def _clean_name(display_name: str) -> str:
    return ' '.join(str(display_name).strip().split())


def hash_pin(display_name: str, pin: str) -> str:
    normalized = _clean_name(display_name).lower()
    raw = f'{PEPPER}|{normalized}|{str(pin).strip()}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def login_or_create_user(display_name: str, pin: str, create_if_missing: bool = True) -> dict:
    init_database()
    name = _clean_name(display_name)
    pin_text = str(pin).strip()
    if not name:
        raise ValueError('学习者名称不能为空。')
    if len(pin_text) < 4:
        raise ValueError('PIN 至少需要4位。')

    with get_connection() as conn:
        row = conn.execute(select(users).where(users.c.display_name == name)).mappings().first()
        pin_hash = hash_pin(name, pin_text)
        if row:
            if row['pin_hash'] != pin_hash:
                raise ValueError('PIN 不正确。')
            user = dict(row)
        else:
            if not create_if_missing:
                raise ValueError('该学习者不存在。')
            result = conn.execute(
                insert(users).values(display_name=name, pin_hash=pin_hash, created_at=datetime.now())
            )
            user_id = int(result.inserted_primary_key[0])
            user = {'id': user_id, 'display_name': name}
    ensure_user_word_status(int(user['id']))
    return {'id': int(user['id']), 'display_name': str(user['display_name'])}
