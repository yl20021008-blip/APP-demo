from __future__ import annotations

import io
from typing import BinaryIO

import pandas as pd

from modules.database import get_connection

COLUMN_MAPPING = {
    "Number": "original_number",
    "Words": "word",
    "词性": "part_of_speech",
    "Annotation": "annotation",
    "expand": "expansion",
    "固定搭配": "collocation",
    "Example Sentence": "example_sentence",
}

OUTPUT_COLUMNS = [
    "original_number",
    "word",
    "part_of_speech",
    "annotation",
    "expansion",
    "collocation",
    "example_sentence",
    "self_reported_known",
]


def read_uploaded_excel(uploaded_file: BinaryIO) -> pd.DataFrame:
    content = uploaded_file.read()
    uploaded_file.seek(0)
    raw_df = pd.read_excel(io.BytesIO(content))
    return clean_dataframe(raw_df)


def clean_dataframe(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    df = df.dropna(axis=0, how="all").dropna(axis=1, how="all")

    if len(df.columns) == 0:
        raise ValueError("表格为空。")

    first_column = df.columns[0]
    if first_column not in COLUMN_MAPPING:
        df = df.rename(columns={first_column: "熟悉标记"})

    missing = [name for name in ("Words", "Annotation") if name not in df.columns]
    if missing:
        raise ValueError(f"缺少必要字段：{', '.join(missing)}")

    mapping = {
        source: target
        for source, target in COLUMN_MAPPING.items()
        if source in df.columns
    }
    df = df.rename(columns=mapping)

    if "熟悉标记" in df.columns:
        df["self_reported_known"] = (
            df["熟悉标记"]
            .fillna("")
            .astype(str)
            .str.strip()
            .isin(["√", "✓", "1", "是", "熟悉"])
            .astype(int)
        )
    else:
        df["self_reported_known"] = 0

    for column in COLUMN_MAPPING.values():
        if column not in df.columns:
            df[column] = None

    df["word"] = df["word"].fillna("").astype(str).str.strip().str.lower()
    df["part_of_speech"] = (
        df["part_of_speech"].fillna("").astype(str).str.strip()
    )
    df["annotation"] = (
        df["annotation"].fillna("").astype(str).str.strip()
    )

    df = df[df["word"] != ""]
    df = df.drop_duplicates(
        subset=["word", "part_of_speech"],
        keep="first",
    )

    return df[OUTPUT_COLUMNS].reset_index(drop=True)


def import_words(
    df: pd.DataFrame,
    chapter: str,
    book_name: str = "雅思词汇真经",
) -> tuple[int, int]:
    chapter = chapter.strip()
    if not chapter:
        raise ValueError("章节名称不能为空。")

    inserted = 0
    duplicated = 0

    with get_connection() as connection:
        for row in df.to_dict(orient="records"):
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO words (
                    book_name,
                    chapter,
                    original_number,
                    word,
                    part_of_speech,
                    annotation,
                    expansion,
                    collocation,
                    example_sentence,
                    self_reported_known
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    book_name,
                    chapter,
                    _safe_value(row.get("original_number")),
                    _safe_text(row.get("word")),
                    _safe_text(row.get("part_of_speech")),
                    _safe_text(row.get("annotation")),
                    _safe_text(row.get("expansion")),
                    _safe_text(row.get("collocation")),
                    _safe_text(row.get("example_sentence")),
                    int(row.get("self_reported_known", 0)),
                ),
            )

            if cursor.rowcount == 1:
                inserted += 1
                word_id = cursor.lastrowid
                connection.execute(
                    """
                    INSERT INTO learning_status(
                        word_id,
                        status,
                        mastery_level
                    )
                    VALUES (?, 'new', 0)
                    """,
                    (word_id,),
                )
            else:
                duplicated += 1

    return inserted, duplicated


def _safe_text(value: object) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _safe_value(value: object) -> object | None:
    if pd.isna(value):
        return None
    return value
