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
    case,
    insert,
    select,
    text,
)
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.pool import QueuePool

APP_DIR = Path(__file__).resolve().parents[1]
LOCAL_DB_PATH = APP_DIR / "database" / "vocabulary.db"

metadata = MetaData()

users = Table(
    "users", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("display_name", String(120), nullable=False, unique=True),
    Column("pin_hash", String(128), nullable=False),
    Column("created_at", DateTime, nullable=False, default=datetime.now),
)

words = Table(
    "words", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("book_name", String(200), nullable=False, default="雅思词汇真经"),
    Column("chapter", String(200), nullable=False, default="未分组"),
    Column("original_number", Integer),
    Column("word", String(200), nullable=False),
    Column("part_of_speech", String(120)),
    Column("annotation", Text),
    Column("expansion", Text),
    Column("collocation", Text),
    Column("example_sentence", Text),
    Column("self_reported_known", Integer, nullable=False, default=0),
    Column("uk_phonetic", String(200)),
    Column("us_phonetic", String(200)),
    Column("uk_audio_url", Text),
    Column("us_audio_url", Text),
    Column("example_translation", Text),
    Column("example_source", String(200)),
    Column("translation_source", String(200)),
    Column("enrichment_status", String(40), nullable=False, default="pending"),
    Column("enrichment_error", Text),
    Column("enrichment_attempts", Integer, nullable=False, default=0),
    Column("last_enriched_at", DateTime),
    Column("created_at", DateTime, nullable=False, default=datetime.now),
    UniqueConstraint("word", "part_of_speech", "chapter", name="uq_words_word_pos_chapter"),
)

learning_status = Table(
    "learning_status", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("word_id", Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
    Column("status", String(40), nullable=False, default="new"),
    Column("mastery_level", Integer, nullable=False, default=0),
    Column("first_learned_at", DateTime),
    Column("last_review_at", DateTime),
    Column("next_review_at", DateTime),
    Column("total_reviews", Integer, nullable=False, default=0),
    Column("correct_count", Integer, nullable=False, default=0),
    Column("wrong_count", Integer, nullable=False, default=0),
    Column("fuzzy_count", Integer, nullable=False, default=0),
    Column("consecutive_correct", Integer, nullable=False, default=0),
    Column("difficult_flag", Integer, nullable=False, default=0),
    UniqueConstraint("user_id", "word_id", name="uq_learning_user_word"),
)

review_logs = Table(
    "review_logs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("word_id", Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
    Column("reviewed_at", DateTime, nullable=False, default=datetime.now),
    Column("result", String(40), nullable=False),
    Column("question_type", String(80), nullable=False, default="english_to_chinese"),
    Column("old_level", Integer, nullable=False),
    Column("new_level", Integer, nullable=False),
    Column("next_review_at", DateTime),
)

app_settings = Table(
    "app_settings", metadata,
    Column("setting_key", String(120), primary_key=True),
    Column("setting_value", Text, nullable=False),
)

enrichment_cache = Table(
    "enrichment_cache", metadata,
    Column("word", String(200), primary_key=True),
    Column("payload_json", Text, nullable=False),
    Column("source", String(200), nullable=False),
    Column("fetched_at", DateTime, nullable=False),
)

story_groups = Table(
    "story_groups", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("group_number", Integer, nullable=False),
    Column("title_en", Text, nullable=False),
    Column("title_zh", Text, nullable=False),
    Column("story_en", Text, nullable=False),
    Column("story_zh", Text, nullable=False),
    Column("memory_tip", Text),
    Column("style", String(120), nullable=False, default="IELTS memory story"),
    Column("provider", String(120), nullable=False, default="local_template"),
    Column("word_count", Integer, nullable=False, default=0),
    Column("created_at", DateTime, nullable=False, default=datetime.now),
    UniqueConstraint("user_id", "group_number", name="uq_story_user_group"),
)

story_group_items = Table(
    "story_group_items", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("story_group_id", Integer, ForeignKey("story_groups.id", ondelete="CASCADE"), nullable=False),
    Column("word_id", Integer, ForeignKey("words.id", ondelete="CASCADE"), nullable=False),
    Column("position", Integer, nullable=False),
    Column("sentence_en", Text),
    Column("sentence_zh", Text),
    UniqueConstraint("story_group_id", "word_id", name="uq_story_item_story_word"),
    UniqueConstraint("user_id", "word_id", name="uq_story_item_user_word"),
)

_ENGINE: Engine | None = None
_DATABASE_INITIALIZED = False


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
    url = _read_secret("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        return url
    LOCAL_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{LOCAL_DB_PATH}"


def get_database_mode() -> str:
    url = get_database_url()
    return "cloud-postgres" if url.startswith("postgresql") else "local-sqlite"


def get_engine() -> Engine:
    """复用数据库连接池。

    v1.3 以前使用 NullPool，每次查询都重连 Supabase，云端会明显变慢。
    v1.3.1 改成小连接池 + pool_pre_ping，适合 Streamlit Cloud。
    """
    global _ENGINE
    if _ENGINE is None:
        url = get_database_url()
        kwargs = {"future": True, "pool_pre_ping": True}
        if url.startswith("postgresql"):
            kwargs.update(
                {
                    "poolclass": QueuePool,
                    "pool_size": 2,
                    "max_overflow": 1,
                    "pool_timeout": 20,
                    "pool_recycle": 180,
                }
            )
        _ENGINE = create_engine(url, **kwargs)
    return _ENGINE


@contextmanager
def get_connection() -> Iterator[Connection]:
    with get_engine().begin() as connection:
        yield connection


def _create_indexes(conn: Connection) -> None:
    """为常用查询创建索引。PostgreSQL / SQLite 都支持 IF NOT EXISTS。"""
    index_sql = [
        "CREATE INDEX IF NOT EXISTS idx_words_chapter ON words(chapter)",
        "CREATE INDEX IF NOT EXISTS idx_words_word ON words(word)",
        "CREATE INDEX IF NOT EXISTS idx_words_enrichment ON words(enrichment_status, last_enriched_at)",
        "CREATE INDEX IF NOT EXISTS idx_learning_user_status ON learning_status(user_id, status)",
        "CREATE INDEX IF NOT EXISTS idx_learning_user_due ON learning_status(user_id, status, next_review_at)",
        "CREATE INDEX IF NOT EXISTS idx_learning_user_difficult ON learning_status(user_id, difficult_flag)",
        "CREATE INDEX IF NOT EXISTS idx_review_user_time ON review_logs(user_id, reviewed_at)",
        "CREATE INDEX IF NOT EXISTS idx_story_user_group ON story_groups(user_id, group_number)",
        "CREATE INDEX IF NOT EXISTS idx_story_items_user_word ON story_group_items(user_id, word_id)",
    ]
    for sql in index_sql:
        try:
            conn.execute(text(sql))
        except Exception:
            # 索引创建失败不应阻断应用启动。
            pass


def init_database(force: bool = False) -> None:
    """初始化数据库。

    性能优化：同一个 Streamlit 进程内只 create_all 一次，避免每次页面刷新都检查全部表。
    """
    global _DATABASE_INITIALIZED
    if _DATABASE_INITIALIZED and not force:
        return

    engine = get_engine()
    metadata.create_all(engine)

    with engine.begin() as conn:
        defaults = {
            "daily_new_limit": "20",
            "daily_review_limit": "200",
            "story_group_size": "30",
        }
        for key, value in defaults.items():
            exists = conn.execute(
                select(app_settings.c.setting_key).where(app_settings.c.setting_key == key)
            ).first()
            if not exists:
                conn.execute(insert(app_settings).values(setting_key=key, setting_value=value))
        _create_indexes(conn)

    _DATABASE_INITIALIZED = True


def ensure_user_word_status(user_id: int) -> int:
    """给当前学习者补齐所有公共词库的学习状态。

    性能优化：由 Python 全量扫描改成数据库侧 INSERT SELECT，避免大词库时卡顿。
    """
    init_database()
    mode = get_database_mode()
    sql_pg = """
        INSERT INTO learning_status (user_id, word_id, status, mastery_level)
        SELECT :user_id, w.id, 'new', 0
        FROM words w
        LEFT JOIN learning_status ls
          ON ls.user_id = :user_id AND ls.word_id = w.id
        WHERE ls.word_id IS NULL
        ON CONFLICT (user_id, word_id) DO NOTHING
    """
    sql_sqlite = """
        INSERT OR IGNORE INTO learning_status (user_id, word_id, status, mastery_level)
        SELECT :user_id, w.id, 'new', 0
        FROM words w
        LEFT JOIN learning_status ls
          ON ls.user_id = :user_id AND ls.word_id = w.id
        WHERE ls.word_id IS NULL
    """
    with get_connection() as conn:
        before = conn.execute(
            select(func.count()).select_from(learning_status).where(
                learning_status.c.user_id == int(user_id)
            )
        ).scalar_one()
        conn.execute(text(sql_pg if mode == "cloud-postgres" else sql_sqlite), {"user_id": int(user_id)})
        after = conn.execute(
            select(func.count()).select_from(learning_status).where(
                learning_status.c.user_id == int(user_id)
            )
        ).scalar_one()
    return int(after or 0) - int(before or 0)


def get_dashboard_metrics(user_id: int | None = None) -> dict[str, int]:
    init_database()
    now = datetime.now()
    with get_connection() as conn:
        total_words = conn.execute(select(func.count()).select_from(words)).scalar_one()
        total_users = conn.execute(select(func.count()).select_from(users)).scalar_one()

        if user_id is None:
            return {
                "total_words": int(total_words or 0),
                "new_words": 0,
                "due_reviews": 0,
                "learned_words": 0,
                "total_users": int(total_users or 0),
            }

        ensure_user_word_status(int(user_id))

        summary = conn.execute(
            select(
                func.sum(case((learning_status.c.status == "new", 1), else_=0)).label("new_words"),
                func.sum(case((learning_status.c.status != "new", 1), else_=0)).label("learned_words"),
                func.sum(
                    func.case(
                        (
                            (learning_status.c.status != "new")
                            & learning_status.c.next_review_at.is_not(None)
                            & (learning_status.c.next_review_at <= now),
                            1,
                        ),
                        else_=0,
                    )
                ).label("due_reviews"),
            ).where(learning_status.c.user_id == int(user_id))
        ).mappings().first()

    return {
        "total_words": int(total_words or 0),
        "new_words": int((summary or {}).get("new_words") or 0),
        "due_reviews": int((summary or {}).get("due_reviews") or 0),
        "learned_words": int((summary or {}).get("learned_words") or 0),
        "total_users": int(total_users or 0),
    }
