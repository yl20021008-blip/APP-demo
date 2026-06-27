from __future__ import annotations

import io
import re
from pathlib import Path
from typing import BinaryIO

import pandas as pd
from sqlalchemy import insert, select, update

from modules.database import get_connection, init_database, words, ensure_user_word_status

FIELD_ALIASES: dict[str, list[str]] = {
    "original_number": ["Number", "No", "No.", "序号", "编号", "sort", "Sort", "index", "id"],
    "word": ["Words", "Word", "word", "words", "单词", "词汇", "英文", "vocabulary"],
    "part_of_speech": ["词性", "part_of_speech", "pos", "POS", "type", "词类"],
    "annotation": ["Annotation", "meaning", "Meaning", "中文释义", "释义", "释意", "中文", "翻译", "definition"],
    "expansion": ["expand", "Expand", "expansion", "派生", "派生词", "拓展", "扩展"],
    "collocation": ["固定搭配", "collocation", "Collocation", "搭配", "phrase", "phrases"],
    "example_sentence": ["Example Sentence", "example", "Example", "sentence", "例句", "英文例句"],
    "example_translation": ["Example Translation", "example_translation", "例句翻译", "中文例句", "例句中文"],
    "phonetic": ["phonetic", "Phonetic", "音标", "发音音标", "pronunciation"],
    "uk_phonetic": ["uk_phonetic", "UK phonetic", "英式音标", "英音音标", "British phonetic"],
    "us_phonetic": ["us_phonetic", "US phonetic", "美式音标", "美音音标", "American phonetic"],
    "uk_audio_url": ["uk_audio_url", "英式发音", "英音音频", "uk_audio"],
    "us_audio_url": ["us_audio_url", "美式发音", "美音音频", "us_audio"],
    "chapter": ["Chapter", "chapter", "title", "Title", "章节", "单元", "分类", "category", "Category"],
}
OUTPUT_COLUMNS = [
    "original_number", "word", "part_of_speech", "annotation", "expansion", "collocation",
    "example_sentence", "example_translation", "uk_phonetic", "us_phonetic",
    "uk_audio_url", "us_audio_url", "chapter", "self_reported_known",
]
KNOWN_MARK_ALIASES = ["熟悉标记", "known", "Know", "已掌握", "掌握", "√", "check"]


def _normalize_header(value: object) -> str:
    text = str(value).strip().lower()
    return re.sub(r"[\s_\-\.]+", "", text)


_ALIAS_LOOKUP: dict[str, str] = {}
for canonical, aliases in FIELD_ALIASES.items():
    for alias in aliases:
        _ALIAS_LOOKUP[_normalize_header(alias)] = canonical
_KNOWN_LOOKUP = {_normalize_header(alias) for alias in KNOWN_MARK_ALIASES}


def infer_chapter_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    stem = re.sub(r"[_\-]+", " ", stem).strip()
    stem = re.sub(r"\s+", " ", stem)
    return stem or "未分组"


def read_uploaded_file(uploaded_file: BinaryIO) -> pd.DataFrame:
    filename = getattr(uploaded_file, "name", "uploaded.xlsx")
    suffix = Path(filename).suffix.lower()
    content = uploaded_file.read()
    uploaded_file.seek(0)
    if suffix == ".csv":
        raw_df = _read_csv_bytes(content)
    else:
        raw_df = pd.read_excel(io.BytesIO(content))
    return clean_dataframe(raw_df)


def read_uploaded_excel(uploaded_file: BinaryIO) -> pd.DataFrame:
    return read_uploaded_file(uploaded_file)


def _read_csv_bytes(content: bytes) -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "gb18030", "gbk"]
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return pd.read_csv(io.BytesIO(content), encoding=encoding)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
    raise ValueError(f"CSV读取失败：{last_error}")


def clean_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy().dropna(axis=0, how="all").dropna(axis=1, how="all")
    if len(df.columns) == 0:
        raise ValueError("表格为空。")

    rename_map: dict[object, str] = {}
    known_column: object | None = None
    for column in df.columns:
        normalized = _normalize_header(column)
        if normalized in _ALIAS_LOOKUP:
            canonical = _ALIAS_LOOKUP[normalized]
            if canonical not in rename_map.values():
                rename_map[column] = canonical
        elif normalized in _KNOWN_LOOKUP or str(column).lower().startswith("unnamed"):
            known_column = column
    df = df.rename(columns=rename_map)

    if known_column is not None and "self_reported_known" not in df.columns:
        df["self_reported_known"] = (
            df[known_column].fillna("").astype(str).str.strip()
            .isin(["√", "✓", "1", "true", "True", "是", "熟悉", "已掌握"]).astype(int)
        )
    elif "self_reported_known" not in df.columns:
        df["self_reported_known"] = 0

    missing = [name for name in ["word", "annotation"] if name not in df.columns]
    if missing:
        raise ValueError("缺少必要字段：单词字段 Words/word/单词，以及释义字段 Annotation/meaning/释义。")

    for column in OUTPUT_COLUMNS:
        if column not in df.columns:
            df[column] = None

    if "phonetic" in df.columns:
        phonetic_series = df["phonetic"].apply(_safe_text)
        df["uk_phonetic"] = df["uk_phonetic"].where(df["uk_phonetic"].apply(_safe_text).notna(), phonetic_series)
        df["us_phonetic"] = df["us_phonetic"].where(df["us_phonetic"].apply(_safe_text).notna(), phonetic_series)

    df["word"] = df["word"].fillna("").astype(str).str.strip().str.lower()
    df["part_of_speech"] = df["part_of_speech"].fillna("").astype(str).str.strip()
    df["annotation"] = df["annotation"].fillna("").astype(str).str.strip()
    df["chapter"] = df["chapter"].apply(_safe_text)

    for column in ["expansion", "collocation", "example_sentence", "example_translation", "uk_phonetic", "us_phonetic", "uk_audio_url", "us_audio_url"]:
        df[column] = df[column].apply(_safe_text)

    df["original_number"] = pd.to_numeric(df["original_number"], errors="coerce")
    df["original_number"] = df["original_number"].where(df["original_number"].notna(), None)
    df = df[df["word"] != ""]
    df = df.drop_duplicates(subset=["word", "part_of_speech", "chapter"], keep="first")
    return df[OUTPUT_COLUMNS].reset_index(drop=True)


def import_words(
    df: pd.DataFrame,
    chapter: str | None,
    book_name: str = "雅思词汇真经",
    update_existing: bool = True,
    user_id: int | None = None,
    progress_callback=None,
) -> dict[str, int]:
    """导入词库。

    性能优化：先按章节批量读取已存在词条，再逐条插入/补字段，避免每个词都查一次数据库。
    """
    init_database()
    fallback_chapter = (chapter or "").strip() or "未分组"
    records: list[dict] = []

    for row in df.to_dict(orient="records"):
        row_chapter = _safe_text(row.get("chapter")) or fallback_chapter
        values = {
            "book_name": book_name,
            "chapter": row_chapter,
            "original_number": _safe_int(row.get("original_number")),
            "word": _safe_text(row.get("word")),
            "part_of_speech": _safe_text(row.get("part_of_speech")) or "",
            "annotation": _safe_text(row.get("annotation")),
            "expansion": _safe_text(row.get("expansion")),
            "collocation": _safe_text(row.get("collocation")),
            "example_sentence": _safe_text(row.get("example_sentence")),
            "example_translation": _safe_text(row.get("example_translation")),
            "uk_phonetic": _safe_text(row.get("uk_phonetic")),
            "us_phonetic": _safe_text(row.get("us_phonetic")),
            "uk_audio_url": _safe_text(row.get("uk_audio_url")),
            "us_audio_url": _safe_text(row.get("us_audio_url")),
            "self_reported_known": int(row.get("self_reported_known") or 0),
        }
        if values["word"]:
            values["enrichment_status"] = _infer_enrichment_status(values)
            records.append(values)

    inserted_count = updated_count = duplicated_count = 0
    if not records:
        return {"inserted": 0, "updated": 0, "duplicated": 0}

    chapters = sorted({r["chapter"] for r in records})
    with get_connection() as conn:
        existing_rows = conn.execute(
            select(words).where(words.c.chapter.in_(chapters))
        ).mappings().all()
        existing_map = {
            (str(r["word"]), str(r.get("part_of_speech") or ""), str(r["chapter"])): dict(r)
            for r in existing_rows
        }

        for index, values in enumerate(records, start=1):
            if progress_callback and (index == 1 or index % 100 == 0 or index == len(records)):
                progress_callback(index, len(records), values["word"])

            key = (str(values["word"]), str(values.get("part_of_speech") or ""), str(values["chapter"]))
            existing = existing_map.get(key)

            if existing is None:
                result = conn.execute(insert(words).values(**values))
                inserted_count += 1
                new_id = result.inserted_primary_key[0] if result.inserted_primary_key else None
                if new_id:
                    existing_map[key] = {**values, "id": new_id}
            else:
                patch = {}
                if update_existing:
                    for field, value in values.items():
                        if field in {"word", "part_of_speech", "chapter", "book_name", "self_reported_known"}:
                            continue
                        if _is_blank(existing.get(field)) and not _is_blank(value):
                            patch[field] = value
                    if patch:
                        patch["enrichment_status"] = _infer_enrichment_status({**existing, **patch})
                        conn.execute(update(words).where(words.c.id == existing["id"]).values(**patch))
                        existing.update(patch)
                        updated_count += 1
                    else:
                        duplicated_count += 1
                else:
                    duplicated_count += 1

    if user_id is not None:
        ensure_user_word_status(int(user_id))

    return {"inserted": inserted_count, "updated": updated_count, "duplicated": duplicated_count}


def _infer_enrichment_status(values: dict) -> str:
    has_phonetic = bool(values.get("uk_phonetic") or values.get("us_phonetic"))
    has_example = bool(values.get("example_sentence"))
    has_translation = bool(values.get("example_translation"))
    if has_phonetic and has_example and has_translation:
        return "completed"
    if has_phonetic or has_example or has_translation:
        return "partial"
    return "pending"


def _safe_text(value: object) -> str | None:
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    text = str(value).strip()
    return text or None


def _safe_int(value: object) -> int | None:
    try:
        if pd.isna(value):
            return None
        return int(float(value))
    except Exception:
        return None


def _is_blank(value: object) -> bool:
    return value is None or str(value).strip() == ""
