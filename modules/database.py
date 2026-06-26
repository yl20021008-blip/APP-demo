from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

APP_DIR = Path(__file__).resolve().parents[1]
DB_PATH = APP_DIR / "database" / "vocabulary.db"


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def _column_names(connection: sqlite3.Connection, table_name: str) -> set[str]:
    if not _table_exists(connection, table_name):
        return set()
    rows = connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    return {str(row["name"]) for row in rows}


def _ensure_column(connection: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
    if column_name not in _column_names(connection, table_name):
        connection.execute(f'ALTER TABLE "{table_name}" ADD COLUMN "{column_name}" {definition}')


def init_database() -> None:
    with get_connection() as connection:
        if not _table_exists(connection, "words"):
            connection.execute(
                """
                CREATE TABLE words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_name TEXT NOT NULL DEFAULT '雅思词汇真经',
                    chapter TEXT NOT NULL DEFAULT '未分组',
                    original_number INTEGER,
                    word TEXT NOT NULL,
                    part_of_speech TEXT,
                    annotation TEXT,
                    expansion TEXT,
                    collocation TEXT,
                    example_sentence TEXT,
                    self_reported_known INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(word, part_of_speech, chapter)
                )
                """
            )

        core_columns = {
            "book_name": "TEXT NOT NULL DEFAULT '雅思词汇真经'",
            "chapter": "TEXT NOT NULL DEFAULT '未分组'",
            "original_number": "INTEGER",
            "word": "TEXT",
            "part_of_speech": "TEXT",
            "annotation": "TEXT",
            "expansion": "TEXT",
            "collocation": "TEXT",
            "example_sentence": "TEXT",
            "self_reported_known": "INTEGER NOT NULL DEFAULT 0",
            "created_at": "TEXT",
        }
        for name, definition in core_columns.items():
            _ensure_column(connection, "words", name, definition)

        enrichment_columns = {
            "uk_phonetic": "TEXT",
            "us_phonetic": "TEXT",
            "uk_audio_url": "TEXT",
            "us_audio_url": "TEXT",
            "example_translation": "TEXT",
            "example_source": "TEXT",
            "translation_source": "TEXT",
            "enrichment_status": "TEXT NOT NULL DEFAULT 'pending'",
            "enrichment_error": "TEXT",
            "enrichment_attempts": "INTEGER NOT NULL DEFAULT 0",
            "last_enriched_at": "TEXT",
        }
        for name, definition in enrichment_columns.items():
            _ensure_column(connection, "words", name, definition)

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS learning_status (
                word_id INTEGER PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'new',
                mastery_level INTEGER NOT NULL DEFAULT 0,
                first_learned_at TEXT,
                last_review_at TEXT,
                next_review_at TEXT,
                total_reviews INTEGER NOT NULL DEFAULT 0,
                correct_count INTEGER NOT NULL DEFAULT 0,
                wrong_count INTEGER NOT NULL DEFAULT 0,
                fuzzy_count INTEGER NOT NULL DEFAULT 0,
                consecutive_correct INTEGER NOT NULL DEFAULT 0,
                difficult_flag INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS review_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word_id INTEGER NOT NULL,
                reviewed_at TEXT NOT NULL,
                result TEXT NOT NULL,
                question_type TEXT NOT NULL DEFAULT 'english_to_chinese',
                old_level INTEGER NOT NULL,
                new_level INTEGER NOT NULL,
                next_review_at TEXT,
                FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS enrichment_cache (
                word TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                source TEXT NOT NULL,
                fetched_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                migration_name TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS story_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_number INTEGER NOT NULL UNIQUE,
                title_en TEXT NOT NULL,
                title_zh TEXT NOT NULL,
                story_en TEXT NOT NULL,
                story_zh TEXT NOT NULL,
                memory_tip TEXT,
                style TEXT NOT NULL DEFAULT 'IELTS memory story',
                provider TEXT NOT NULL DEFAULT 'local_template',
                word_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS story_group_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                story_group_id INTEGER NOT NULL,
                word_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                sentence_en TEXT,
                sentence_zh TEXT,
                FOREIGN KEY(story_group_id) REFERENCES story_groups(id) ON DELETE CASCADE,
                FOREIGN KEY(word_id) REFERENCES words(id) ON DELETE CASCADE,
                UNIQUE(story_group_id, word_id),
                UNIQUE(word_id)
            )
            """
        )

        connection.execute(
            """
            INSERT OR IGNORE INTO app_settings(setting_key, setting_value)
            VALUES
                ('daily_new_limit', '20'),
                ('daily_review_limit', '200'),
                ('story_group_size', '30')
            """
        )

        connection.execute(
            """
            INSERT OR IGNORE INTO learning_status(word_id, status, mastery_level)
            SELECT id, 'new', 0 FROM words
            """
        )

        connection.execute(
            """
            UPDATE words
            SET enrichment_status = COALESCE(NULLIF(enrichment_status, ''), 'pending')
            """
        )

        now = datetime.now().isoformat(timespec="seconds")
        connection.execute(
            """
            INSERT OR IGNORE INTO schema_migrations(migration_name, applied_at)
            VALUES ('v0.4_story_memory', ?)
            """,
            (now,),
        )

        connection.execute("CREATE INDEX IF NOT EXISTS idx_learning_due ON learning_status(status, next_review_at)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_words_chapter ON words(chapter)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_words_enrichment ON words(enrichment_status, enrichment_attempts)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_story_items_word ON story_group_items(word_id)")


def get_dashboard_metrics() -> dict[str, int]:
    now = datetime.now().isoformat(timespec="seconds")
    with get_connection() as connection:
        total_words = connection.execute("SELECT COUNT(*) FROM words").fetchone()[0]
        new_words = connection.execute("SELECT COUNT(*) FROM learning_status WHERE status = 'new'").fetchone()[0]
        due_reviews = connection.execute(
            """
            SELECT COUNT(*) FROM learning_status
            WHERE status != 'new' AND next_review_at IS NOT NULL AND next_review_at <= ?
            """,
            (now,),
        ).fetchone()[0]
        learned_words = connection.execute("SELECT COUNT(*) FROM learning_status WHERE status != 'new'").fetchone()[0]

    return {
        "total_words": int(total_words),
        "new_words": int(new_words),
        "due_reviews": int(due_reviews),
        "learned_words": int(learned_words),
    }
