from __future__ import annotations

import json
from datetime import datetime
from typing import Callable

from modules.database import get_connection, init_database
from modules.dictionary_provider import (
    DictionaryLookupError,
    DictionaryResult,
    lookup_word,
)
from modules.translation_provider import (
    TranslationError,
    translate_english_to_chinese,
)

ProgressCallback = Callable[[int, int, str], None]


def get_enrichment_summary(chapter: str | None = None) -> dict[str, int]:
    init_database()

    where_sql = ""
    params: tuple[object, ...] = ()
    if chapter and chapter != "全部":
        where_sql = "WHERE chapter = ?"
        params = (chapter,)

    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT
                COUNT(*) AS total,
                SUM(
                    CASE WHEN COALESCE(uk_phonetic, us_phonetic) IS NULL
                         THEN 1 ELSE 0 END
                ) AS missing_phonetic,
                SUM(
                    CASE WHEN example_sentence IS NULL
                              OR TRIM(example_sentence) = ''
                         THEN 1 ELSE 0 END
                ) AS missing_example,
                SUM(
                    CASE WHEN example_sentence IS NOT NULL
                              AND TRIM(example_sentence) != ''
                              AND (
                                  example_translation IS NULL
                                  OR TRIM(example_translation) = ''
                              )
                         THEN 1 ELSE 0 END
                ) AS missing_translation,
                SUM(
                    CASE WHEN enrichment_status = 'failed'
                         THEN 1 ELSE 0 END
                ) AS failed
            FROM words
            {where_sql}
            """,
            params,
        ).fetchone()

    return {
        "total": int(row["total"] or 0),
        "missing_phonetic": int(row["missing_phonetic"] or 0),
        "missing_example": int(row["missing_example"] or 0),
        "missing_translation": int(row["missing_translation"] or 0),
        "failed": int(row["failed"] or 0),
    }


def _load_cached_dictionary(word: str) -> DictionaryResult | None:
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT payload_json
            FROM enrichment_cache
            WHERE word = ?
            """,
            (word.lower(),),
        ).fetchone()

    if row is None:
        return None

    try:
        payload = json.loads(row["payload_json"])
        return DictionaryResult(**payload)
    except (ValueError, TypeError):
        return None


def _save_dictionary_cache(result: DictionaryResult) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO enrichment_cache(
                word,
                payload_json,
                source,
                fetched_at
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(word)
            DO UPDATE SET
                payload_json = excluded.payload_json,
                source = excluded.source,
                fetched_at = excluded.fetched_at
            """,
            (
                result.word.lower(),
                json.dumps(result.to_dict(), ensure_ascii=False),
                result.source,
                datetime.now().isoformat(timespec="seconds"),
            ),
        )


def _get_dictionary_result(
    word: str,
    force_refresh: bool,
) -> DictionaryResult:
    if not force_refresh:
        cached = _load_cached_dictionary(word)
        if cached is not None:
            return cached

    result = lookup_word(word)
    _save_dictionary_cache(result)
    return result


def _select_words(
    chapter: str | None,
    limit: int,
    retry_failed: bool,
    force_overwrite: bool,
) -> list[dict]:
    conditions: list[str] = []
    params: list[object] = []

    if chapter and chapter != "全部":
        conditions.append("chapter = ?")
        params.append(chapter)

    if retry_failed:
        conditions.append("enrichment_status = 'failed'")
    elif not force_overwrite:
        conditions.append(
            """
            (
                uk_phonetic IS NULL
                OR us_phonetic IS NULL
                OR example_sentence IS NULL
                OR TRIM(COALESCE(example_sentence, '')) = ''
                OR (
                    TRIM(COALESCE(example_sentence, '')) != ''
                    AND TRIM(COALESCE(example_translation, '')) = ''
                )
                OR enrichment_status IN ('pending', 'partial')
            )
            """
        )

    where_sql = "WHERE " + " AND ".join(conditions) if conditions else ""

    params.append(int(limit))
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT *
            FROM words
            {where_sql}
            ORDER BY
                CASE enrichment_status
                    WHEN 'pending' THEN 0
                    WHEN 'partial' THEN 1
                    WHEN 'failed' THEN 2
                    ELSE 3
                END,
                chapter,
                COALESCE(original_number, 999999),
                id
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()

    return [dict(row) for row in rows]


def _status_for(
    uk_phonetic: str | None,
    us_phonetic: str | None,
    example_sentence: str | None,
    example_translation: str | None,
    errors: list[str],
) -> str:
    has_phonetic = bool(uk_phonetic or us_phonetic)
    has_example = bool(example_sentence and example_sentence.strip())
    has_translation = bool(
        example_translation and example_translation.strip()
    )

    if has_phonetic and has_example and has_translation and not errors:
        return "completed"
    if has_phonetic or has_example or has_translation:
        return "partial"
    return "failed"


def enrich_words(
    chapter: str | None = None,
    limit: int = 10,
    fill_missing_example: bool = True,
    translate_example: bool = True,
    retry_failed: bool = False,
    force_overwrite: bool = False,
    translation_provider: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    """
    批量补全音标、发音、缺失例句与例句翻译。

    原则：
    - 默认只补空白，不覆盖原书已有内容；
    - 原书无例句时，才采用词典例句；
    - 每个词单独写入数据库，一个失败不影响整批；
    - 所有失败都会记录并可重试。
    """
    init_database()
    rows = _select_words(
        chapter=chapter,
        limit=max(1, int(limit)),
        retry_failed=retry_failed,
        force_overwrite=force_overwrite,
    )

    results: list[dict] = []
    success_count = 0
    partial_count = 0
    failed_count = 0
    total = len(rows)

    for index, row in enumerate(rows, start=1):
        word = str(row.get("word") or "").strip()
        if progress_callback:
            progress_callback(index, total, word)

        errors: list[str] = []
        dictionary_result: DictionaryResult | None = None

        try:
            dictionary_result = _get_dictionary_result(
                word,
                force_refresh=force_overwrite,
            )
        except DictionaryLookupError as exc:
            errors.append(str(exc))

        existing_uk = row.get("uk_phonetic")
        existing_us = row.get("us_phonetic")
        existing_uk_audio = row.get("uk_audio_url")
        existing_us_audio = row.get("us_audio_url")
        existing_example = row.get("example_sentence")
        existing_translation = row.get("example_translation")
        existing_example_source = row.get("example_source")
        existing_translation_source = row.get("translation_source")

        if dictionary_result:
            uk_phonetic = (
                dictionary_result.uk_phonetic
                if force_overwrite or not existing_uk
                else existing_uk
            )
            us_phonetic = (
                dictionary_result.us_phonetic
                if force_overwrite or not existing_us
                else existing_us
            )
            uk_audio = (
                dictionary_result.uk_audio_url
                if force_overwrite or not existing_uk_audio
                else existing_uk_audio
            )
            us_audio = (
                dictionary_result.us_audio_url
                if force_overwrite or not existing_us_audio
                else existing_us_audio
            )
        else:
            uk_phonetic = existing_uk
            us_phonetic = existing_us
            uk_audio = existing_uk_audio
            us_audio = existing_us_audio

        example_sentence = existing_example
        example_source = existing_example_source
        if existing_example and str(existing_example).strip():
            example_source = existing_example_source or "雅思词汇真经"
        elif fill_missing_example and dictionary_result:
            example_sentence = dictionary_result.example_sentence
            if example_sentence:
                example_source = dictionary_result.source

        example_translation = existing_translation
        translation_source = existing_translation_source

        should_translate = (
            translate_example
            and example_sentence
            and str(example_sentence).strip()
            and (force_overwrite or not existing_translation)
        )

        if should_translate:
            try:
                example_translation, translation_source = (
                    translate_english_to_chinese(
                        str(example_sentence),
                        provider=translation_provider,
                    )
                )
            except TranslationError as exc:
                errors.append(str(exc))

        status = _status_for(
            uk_phonetic=uk_phonetic,
            us_phonetic=us_phonetic,
            example_sentence=example_sentence,
            example_translation=example_translation,
            errors=errors,
        )

        with get_connection() as connection:
            connection.execute(
                """
                UPDATE words
                SET
                    uk_phonetic = ?,
                    us_phonetic = ?,
                    uk_audio_url = ?,
                    us_audio_url = ?,
                    example_sentence = ?,
                    example_translation = ?,
                    example_source = ?,
                    translation_source = ?,
                    enrichment_status = ?,
                    enrichment_error = ?,
                    enrichment_attempts =
                        COALESCE(enrichment_attempts, 0) + 1,
                    last_enriched_at = ?
                WHERE id = ?
                """,
                (
                    uk_phonetic,
                    us_phonetic,
                    uk_audio,
                    us_audio,
                    example_sentence,
                    example_translation,
                    example_source,
                    translation_source,
                    status,
                    "；".join(errors) if errors else None,
                    datetime.now().isoformat(timespec="seconds"),
                    int(row["id"]),
                ),
            )

        if status == "completed":
            success_count += 1
        elif status == "partial":
            partial_count += 1
        else:
            failed_count += 1

        results.append(
            {
                "单词": word,
                "状态": status,
                "英式音标": uk_phonetic or "",
                "美式音标": us_phonetic or "",
                "例句来源": example_source or "",
                "翻译来源": translation_source or "",
                "错误": "；".join(errors),
            }
        )

    return {
        "processed": total,
        "completed": success_count,
        "partial": partial_count,
        "failed": failed_count,
        "items": results,
    }
