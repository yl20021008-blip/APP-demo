from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

try:
    import streamlit as st
except Exception:  # noqa: BLE001
    st = None
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    insert,
    select,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.pool import NullPool

APP_DIR = Path(__file__).resolve().parents[1]
LOCAL_DB_PATH = APP_DIR / 'database' / 'vocabulary.db'

metadata = MetaData()

users = Table(
    'users', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('display_name', String(120), nullable=False, unique=True),
    Column('pin_hash', String(128), nullable=False),
    Column('created_at', DateTime, nullable=False, default=datetime.now),
)

words = Table(
    'words', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('book_name', String(200), nullable=False, default='雅思词汇真经'),
    Column('chapter', String(200), nullable=False, default='未分组'),
    Column('original_number', Integer),
    Column('word', String(200), nullable=False),
    Column('part_of_speech', String(120)),
    Column('annotation', Text),
    Column('expansion', Text),
    Column('collocation', Text),
    Column('example_sentence', Text),
    Column('self_reported_known', Integer, nullable=False, default=0),
    Column('uk_phonetic', String(200)),
    Column('us_phonetic', String(200)),
    Column('uk_audio_url', Text),
    Column('us_audio_url', Text),
    Column('example_translation', Text),
    Column('example_source', String(200)),
    Column('translation_source', String(200)),
    Column('enrichment_status', String(40), nullable=False, default='pending'),
    Column('enrichment_error', Text),
    Column('enrichment_attempts', Integer, nullable=False, default=0),
    Column('last_enriched_at', DateTime),
    Column('created_at', DateTime, nullable=False, default=datetime.now),
    UniqueConstraint('word', 'part_of_speech', 'chapter', name='uq_words_word_pos_chapter'),
)

learning_status = Table(
    'learning_status', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('word_id', Integer, ForeignKey('words.id', ondelete='CASCADE'), nullable=False),
    Column('status', String(40), nullable=False, default='new'),
    Column('mastery_level', Integer, nullable=False, default=0),
    Column('first_learned_at', DateTime),
    Column('last_review_at', DateTime),
    Column('next_review_at', DateTime),
    Column('total_reviews', Integer, nullable=False, default=0),
    Column('correct_count', Integer, nullable=False, default=0),
    Column('wrong_count', Integer, nullable=False, default=0),
    Column('fuzzy_count', Integer, nullable=False, default=0),
    Column('consecutive_correct', Integer, nullable=False, default=0),
    Column('difficult_flag', Integer, nullable=False, default=0),
    UniqueConstraint('user_id', 'word_id', name='uq_learning_user_word'),
)

review_logs = Table(
    'review_logs', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('word_id', Integer, ForeignKey('words.id', ondelete='CASCADE'), nullable=False),
    Column('reviewed_at', DateTime, nullable=False, default=datetime.now),
    Column('result', String(40), nullable=False),
    Column('question_type', String(80), nullable=False, default='english_to_chinese'),
    Column('old_level', Integer, nullable=False),
    Column('new_level', Integer, nullable=False),
    Column('next_review_at', DateTime),
)

app_settings = Table(
    'app_settings', metadata,
    Column('setting_key', String(120), primary_key=True),
    Column('setting_value', Text, nullable=False),
)

enrichment_cache = Table(
    'enrichment_cache', metadata,
    Column('word', String(200), primary_key=True),
    Column('payload_json', Text, nullable=False),
    Column('source', String(200), nullable=False),
    Column('fetched_at', DateTime, nullable=False),
)

story_groups = Table(
    'story_groups', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('group_number', Integer, nullable=False),
    Column('title_en', Text, nullable=False),
    Column('title_zh', Text, nullable=False),
    Column('story_en', Text, nullable=False),
    Column('story_zh', Text, nullable=False),
    Column('memory_tip', Text),
    Column('style', String(120), nullable=False, default='IELTS memory story'),
    Column('provider', String(120), nullable=False, default='local_template'),
    Column('word_count', Integer, nullable=False, default=0),
    Column('created_at', DateTime, nullable=False, default=datetime.now),
    UniqueConstraint('user_id', 'group_number', name='uq_story_user_group'),
)

story_group_items = Table(
    'story_group_items', metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('story_group_id', Integer, ForeignKey('story_groups.id', ondelete='CASCADE'), nullable=False),
    Column('word_id', Integer, ForeignKey('words.id', ondelete='CASCADE'), nullable=False),
    Column('position', Integer, nullable=False),
    Column('sentence_en', Text),
    Column('sentence_zh', Text),
    UniqueConstraint('story_group_id', 'word_id', name='uq_story_item_story_word'),
    UniqueConstraint('user_id', 'word_id', name='uq_story_item_user_word'),
)

_ENGINE: Engine | None = None


def _read_secret(name: str) -> str | None:
    if st is not None:
        try:
            value = st.secrets.get(name)
            if value:
                return str(value)
        except Exception:
            pass
    return os.getenv(name)


def get_database_url() -> str:
    url = _read_secret('DATABASE_URL')
    if url:
        # SQLAlchemy 新版本建议 postgresql://，兼容 postgres://。
        if url.startswith('postgres://'):
            url = 'postgresql://' + url[len('postgres://'):]
        return url
    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f'sqlite:///{LOCAL_DB_PATH}'


def get_database_mode() -> str:
    url = get_database_url()
    return 'cloud-postgres' if url.startswith('postgresql') else 'local-sqlite'


def get_engine() -> Engine:
    global _ENGINE
    if _ENGINE is None:
        url = get_database_url()
        kwargs = {'future': True, 'pool_pre_ping': True}
        if url.startswith('postgresql'):
            # Streamlit Cloud/Supabase 场景下使用短连接，避免连接池残留。
            kwargs['poolclass'] = NullPool
        _ENGINE = create_engine(url, **kwargs)
    return _ENGINE


@contextmanager
def get_connection() -> Iterator[Connection]:
    engine = get_engine()
    with engine.begin() as connection:
        yield connection


def init_database() -> None:
    engine = get_engine()
    metadata.create_all(engine)
    with engine.begin() as conn:
        defaults = {
            'daily_new_limit': '20',
            'daily_review_limit': '200',
            'story_group_size': '30',
        }
        for key, value in defaults.items():
            exists = conn.execute(
                select(app_settings.c.setting_key).where(app_settings.c.setting_key == key)
            ).first()
            if not exists:
                conn.execute(insert(app_settings).values(setting_key=key, setting_value=value))


def ensure_user_word_status(user_id: int) -> int:
    """给当前学习者补齐所有公共词库的学习状态。返回新增状态数量。"""
    init_database()
    with get_connection() as conn:
        all_word_ids = [r[0] for r in conn.execute(select(words.c.id)).all()]
        if not all_word_ids:
            return 0
        existing_word_ids = set(
            r[0] for r in conn.execute(
                select(learning_status.c.word_id).where(learning_status.c.user_id == int(user_id))
            ).all()
        )
        missing = [wid for wid in all_word_ids if wid not in existing_word_ids]
        if missing:
            conn.execute(
                insert(learning_status),
                [{'user_id': int(user_id), 'word_id': int(wid), 'status': 'new', 'mastery_level': 0}
                 for wid in missing]
            )
        return len(missing)


def get_dashboard_metrics(user_id: int | None = None) -> dict[str, int]:
    init_database()
    now = datetime.now()
    with get_connection() as conn:
        total_words = conn.execute(select(func.count()).select_from(words)).scalar_one()
        total_users = conn.execute(select(func.count()).select_from(users)).scalar_one()
        if user_id is None:
            return {
                'total_words': int(total_words or 0),
                'new_words': 0,
                'due_reviews': 0,
                'learned_words': 0,
                'total_users': int(total_users or 0),
            }
        ensure_user_word_status(int(user_id))
        new_words = conn.execute(
            select(func.count()).select_from(learning_status).where(
                learning_status.c.user_id == int(user_id),
                learning_status.c.status == 'new',
            )
        ).scalar_one()
        learned_words = conn.execute(
            select(func.count()).select_from(learning_status).where(
                learning_status.c.user_id == int(user_id),
                learning_status.c.status != 'new',
            )
        ).scalar_one()
        due_reviews = conn.execute(
            select(func.count()).select_from(learning_status).where(
                learning_status.c.user_id == int(user_id),
                learning_status.c.status != 'new',
                learning_status.c.next_review_at.is_not(None),
                learning_status.c.next_review_at <= now,
            )
        ).scalar_one()
    return {
        'total_words': int(total_words or 0),
        'new_words': int(new_words or 0),
        'due_reviews': int(due_reviews or 0),
        'learned_words': int(learned_words or 0),
        'total_users': int(total_users or 0),
    }
