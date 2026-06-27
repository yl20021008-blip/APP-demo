from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import case, delete, func, select, text

from modules.database import (
    get_connection,
    init_database,
    learning_status,
    review_logs,
    story_group_items,
    story_groups,
    users,
    words,
    ensure_user_word_status,
)
from modules.importer import import_words, read_uploaded_file


def _read_secret(name: str) -> str | None:
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name)


def get_admin_pin() -> str | None:
    return _read_secret("ADMIN_PIN")


def is_admin_enabled() -> bool:
    return bool(get_admin_pin())


def is_admin() -> bool:
    return bool(st.session_state.get("is_admin"))


def admin_login(pin: str) -> bool:
    expected = get_admin_pin()
    if not expected:
        return False
    ok = str(pin or "").strip() == str(expected).strip()
    if ok:
        st.session_state["is_admin"] = True
    return ok


def admin_logout() -> None:
    st.session_state.pop("is_admin", None)


def get_public_edit_locked() -> bool:
    value = _read_secret("PUBLIC_WORDLIST_LOCKED")
    if value is None:
        return True
    return str(value).strip().lower() not in {"false", "0", "no", "off"}


def require_admin_for_public_write(action_name: str = "管理公共词库") -> bool:
    if not get_public_edit_locked():
        return True

    if is_admin():
        return True

    st.warning(f"公共词库已锁定。只有管理员可以{action_name}。普通学习者只能学习、复习和生成自己的故事。")
    st.info("请到“公共词库管理”页面输入管理员 PIN。")
    return False


def get_chapter_summary() -> pd.DataFrame:
    init_database()
    with get_connection() as conn:
        rows = conn.execute(
            select(
                words.c.chapter.label("chapter"),
                func.count(words.c.id).label("word_count"),
                func.sum(case((words.c.example_sentence.is_not(None), 1), else_=0)).label("example_count"),
                func.sum(case((words.c.uk_phonetic.is_not(None), 1), else_=0)).label("phonetic_count"),
            )
            .group_by(words.c.chapter)
            .order_by(words.c.chapter)
        ).mappings().all()

    return pd.DataFrame(
        [
            {
                "章节": r["chapter"],
                "词数": int(r["word_count"] or 0),
                "有例句": int(r["example_count"] or 0),
                "有音标": int(r["phonetic_count"] or 0),
            }
            for r in rows
        ]
    )


def get_wordbook_export_df() -> pd.DataFrame:
    init_database()
    with get_connection() as conn:
        rows = conn.execute(
            select(
                words.c.book_name,
                words.c.chapter,
                words.c.original_number,
                words.c.word,
                words.c.part_of_speech,
                words.c.annotation,
                words.c.expansion,
                words.c.collocation,
                words.c.example_sentence,
                words.c.example_translation,
                words.c.example_source,
                words.c.uk_phonetic,
                words.c.us_phonetic,
                words.c.uk_audio_url,
                words.c.us_audio_url,
                words.c.enrichment_status,
                words.c.created_at,
            )
            .order_by(words.c.chapter, words.c.original_number, words.c.id)
        ).mappings().all()

    return pd.DataFrame(
        [
            {
                "Book": r["book_name"],
                "Chapter": r["chapter"],
                "Number": r["original_number"],
                "Words": r["word"],
                "词性": r["part_of_speech"],
                "Annotation": r["annotation"],
                "expand": r["expansion"],
                "固定搭配": r["collocation"],
                "Example Sentence": r["example_sentence"],
                "Example Translation": r["example_translation"],
                "Example Source": r["example_source"],
                "uk_phonetic": r["uk_phonetic"],
                "us_phonetic": r["us_phonetic"],
                "uk_audio_url": r["uk_audio_url"],
                "us_audio_url": r["us_audio_url"],
                "enrichment_status": r["enrichment_status"],
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    )


def export_wordbook_excel_bytes() -> bytes:
    df = get_wordbook_export_df()
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Public_Wordbook")
        get_chapter_summary().to_excel(writer, index=False, sheet_name="Chapter_Summary")
    return buffer.getvalue()


def delete_chapter(chapter: str) -> int:
    init_database()
    if not chapter:
        return 0
    with get_connection() as conn:
        ids = [int(r[0]) for r in conn.execute(select(words.c.id).where(words.c.chapter == chapter)).all()]
        if not ids:
            return 0
        conn.execute(delete(story_group_items).where(story_group_items.c.word_id.in_(ids)))
        conn.execute(delete(review_logs).where(review_logs.c.word_id.in_(ids)))
        conn.execute(delete(learning_status).where(learning_status.c.word_id.in_(ids)))
        result = conn.execute(delete(words).where(words.c.id.in_(ids)))
    return int(result.rowcount or 0)


def clear_public_wordbook() -> dict[str, int]:
    init_database()
    with get_connection() as conn:
        story_items = conn.execute(delete(story_group_items)).rowcount or 0
        reviews = conn.execute(delete(review_logs)).rowcount or 0
        status = conn.execute(delete(learning_status)).rowcount or 0
        stories = conn.execute(delete(story_groups)).rowcount or 0
        word_count = conn.execute(delete(words)).rowcount or 0
    return {
        "deleted_words": int(word_count),
        "deleted_learning_status": int(status),
        "deleted_review_logs": int(reviews),
        "deleted_story_items": int(story_items),
        "deleted_stories": int(stories),
    }


def sync_all_users_learning_status() -> int:
    init_database()
    with get_connection() as conn:
        user_ids = [int(r[0]) for r in conn.execute(select(users.c.id)).all()]
    total = 0
    for user_id in user_ids:
        total += ensure_user_word_status(user_id)
    return total


class NamedBytesIO(BytesIO):
    def __init__(self, payload: bytes, name: str):
        super().__init__(payload)
        self.name = name


def import_preset_wordbook(update_existing: bool = True) -> dict[str, int | str]:
    init_database()
    preset_path = Path(__file__).resolve().parents[1] / "data" / "default_wordbook.xlsx"
    if not preset_path.exists():
        raise FileNotFoundError("没有找到 data/default_wordbook.xlsx。")

    file_like = NamedBytesIO(preset_path.read_bytes(), "default_wordbook.xlsx")
    df = read_uploaded_file(file_like)
    result = import_words(
        df,
        chapter=None,
        book_name="雅思词汇真经",
        update_existing=update_existing,
        user_id=None,
    )
    synced = sync_all_users_learning_status()
    return {
        **result,
        "synced_learning_status": synced,
        "preset_file": str(preset_path.name),
    }


def reset_to_preset_wordbook() -> dict[str, int | str]:
    cleared = clear_public_wordbook()
    imported = import_preset_wordbook(update_existing=True)
    return {**cleared, **imported}


def try_create_helpful_indexes() -> None:
    init_database()
    statements = [
        "CREATE INDEX IF NOT EXISTS idx_words_chapter_number ON words(chapter, original_number)",
        "CREATE INDEX IF NOT EXISTS idx_words_enrichment_audio ON words(uk_audio_url, us_audio_url)",
        "CREATE INDEX IF NOT EXISTS idx_learning_status_user_word ON learning_status(user_id, word_id)",
        "CREATE INDEX IF NOT EXISTS idx_review_logs_user_word ON review_logs(user_id, word_id)",
    ]
    with get_connection() as conn:
        for stmt in statements:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
