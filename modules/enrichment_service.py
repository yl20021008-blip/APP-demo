from __future__ import annotations

import json
from datetime import datetime
from typing import Callable

from sqlalchemy import and_, case, func, insert, or_, select, update

from modules.database import enrichment_cache, get_connection, init_database, words
from modules.dictionary_provider import DictionaryLookupError, DictionaryResult, lookup_word
from modules.example_provider import build_generated_example
from modules.translation_provider import TranslationError, translate_english_to_chinese

ProgressCallback = Callable[[int, int, str], None]


def _blank(column):
    return or_(column.is_(None), func.trim(func.coalesce(column, "")) == "")


def _not_blank(column):
    return and_(column.is_not(None), func.trim(func.coalesce(column, "")) != "")


def get_enrichment_summary(chapter: str | None = None) -> dict[str, int]:
    init_database()
    conditions = []
    if chapter and chapter != "全部":
        conditions.append(words.c.chapter == chapter)

    stmt = select(
        func.count(words.c.id).label("total"),
        func.sum(case((and_(_blank(words.c.uk_phonetic), _blank(words.c.us_phonetic)), 1), else_=0)).label("missing_phonetic"),
        func.sum(case((and_(_blank(words.c.uk_audio_url), _blank(words.c.us_audio_url)), 1), else_=0)).label("missing_audio"),
        func.sum(case((_blank(words.c.example_sentence), 1), else_=0)).label("missing_example"),
        func.sum(case((and_(_not_blank(words.c.example_sentence), _blank(words.c.example_translation)), 1), else_=0)).label("missing_translation"),
        func.sum(case((words.c.example_source.like("local_generated%"), 1), else_=0)).label("generated_examples"),
        func.sum(case((words.c.enrichment_status == "failed", 1), else_=0)).label("failed"),
    ).select_from(words)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    with get_connection() as conn:
        row = conn.execute(stmt).mappings().first() or {}

    return {
        "total": int(row.get("total") or 0),
        "missing_phonetic": int(row.get("missing_phonetic") or 0),
        "missing_audio": int(row.get("missing_audio") or 0),
        "missing_example": int(row.get("missing_example") or 0),
        "missing_translation": int(row.get("missing_translation") or 0),
        "generated_examples": int(row.get("generated_examples") or 0),
        "failed": int(row.get("failed") or 0),
    }


def _load_cached_dictionary(word: str) -> DictionaryResult | None:
    with get_connection() as conn:
        row = conn.execute(
            select(enrichment_cache.c.payload_json).where(enrichment_cache.c.word == word.lower())
        ).first()
    if row is None:
        return None
    try:
        payload = json.loads(row[0])
        if "example_candidates" not in payload:
            payload["example_candidates"] = []
        return DictionaryResult(**payload)
    except Exception:
        return None


def _save_dictionary_cache(result: DictionaryResult) -> None:
    now = datetime.now()
    payload_json = json.dumps(result.to_dict(), ensure_ascii=False)
    with get_connection() as conn:
        existing = conn.execute(
            select(enrichment_cache.c.word).where(enrichment_cache.c.word == result.word.lower())
        ).first()
        if existing:
            conn.execute(
                update(enrichment_cache)
                .where(enrichment_cache.c.word == result.word.lower())
                .values(payload_json=payload_json, source=result.source, fetched_at=now)
            )
        else:
            conn.execute(
                insert(enrichment_cache).values(
                    word=result.word.lower(),
                    payload_json=payload_json,
                    source=result.source,
                    fetched_at=now,
                )
            )


def _get_dictionary_result(word: str, force_refresh: bool) -> DictionaryResult:
    if not force_refresh:
        cached = _load_cached_dictionary(word)
        if cached is not None:
            return cached
    result = lookup_word(word)
    _save_dictionary_cache(result)
    return result


def _select_words(chapter: str | None, limit: int, retry_failed: bool, force_overwrite: bool) -> list[dict]:
    conditions = []
    if chapter and chapter != "全部":
        conditions.append(words.c.chapter == chapter)

    if retry_failed:
        conditions.append(words.c.enrichment_status == "failed")
    elif not force_overwrite:
        conditions.append(
            or_(
                _blank(words.c.uk_phonetic),
                _blank(words.c.us_phonetic),
                _blank(words.c.uk_audio_url),
                _blank(words.c.us_audio_url),
                _blank(words.c.example_sentence),
                and_(_not_blank(words.c.example_sentence), _blank(words.c.example_translation)),
                words.c.enrichment_status.in_(["pending", "partial"]),
            )
        )

    stmt = select(words).order_by(
        words.c.enrichment_status,
        words.c.chapter,
        words.c.original_number,
        words.c.id,
    ).limit(int(limit))

    if conditions:
        stmt = stmt.where(and_(*conditions))

    with get_connection() as conn:
        rows = conn.execute(stmt).mappings().all()

    return [dict(r) for r in rows]


def _status_for(
    uk_phonetic: str | None,
    us_phonetic: str | None,
    example_sentence: str | None,
    example_translation: str | None,
    errors: list[str],
) -> str:
    has_phonetic = bool(uk_phonetic or us_phonetic)
    has_example = bool(example_sentence and str(example_sentence).strip())
    has_translation = bool(example_translation and str(example_translation).strip())
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
    auto_generate_example: bool = True,
    generated_example_style: str = "ielts",
    progress_callback: ProgressCallback | None = None,
) -> dict:
    init_database()
    rows = _select_words(chapter, max(1, int(limit)), retry_failed, force_overwrite)
    results: list[dict] = []
    success_count = partial_count = failed_count = generated_count = dictionary_example_count = 0
    total = len(rows)

    for index, row in enumerate(rows, start=1):
        word = str(row.get("word") or "").strip()
        if progress_callback:
            progress_callback(index, total, word)

        errors: list[str] = []
        dictionary_result: DictionaryResult | None = None
        dictionary_error: str | None = None

        try:
            dictionary_result = _get_dictionary_result(word, force_refresh=force_overwrite)
        except DictionaryLookupError as exc:
            dictionary_error = str(exc)
            errors.append(str(exc))

        uk_phonetic = row.get("uk_phonetic")
        us_phonetic = row.get("us_phonetic")
        uk_audio = row.get("uk_audio_url")
        us_audio = row.get("us_audio_url")

        if dictionary_result:
            uk_phonetic = dictionary_result.uk_phonetic if force_overwrite or not uk_phonetic else uk_phonetic
            us_phonetic = dictionary_result.us_phonetic if force_overwrite or not us_phonetic else us_phonetic
            uk_audio = dictionary_result.uk_audio_url if force_overwrite or not uk_audio else uk_audio
            us_audio = dictionary_result.us_audio_url if force_overwrite or not us_audio else us_audio

        existing_example = row.get("example_sentence")
        existing_translation = row.get("example_translation")
        example_sentence = existing_example
        example_source = row.get("example_source")
        example_note = ""

        if existing_example and str(existing_example).strip() and not force_overwrite:
            example_source = example_source or "uploaded_wordlist"
        elif fill_missing_example:
            if dictionary_result and dictionary_result.example_sentence:
                example_sentence = dictionary_result.example_sentence
                example_source = dictionary_result.source
                dictionary_example_count += 1
            elif auto_generate_example:
                try:
                    generated = build_generated_example(
                        word=word,
                        part_of_speech=row.get("part_of_speech"),
                        annotation=row.get("annotation"),
                        chapter=row.get("chapter"),
                        style=generated_example_style,
                    )
                    example_sentence = generated.sentence
                    example_source = generated.source
                    example_note = generated.quality_note
                    generated_count += 1
                    errors = [e for e in errors if e != dictionary_error]
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"本地生成例句失败：{exc}")

        example_translation = existing_translation
        translation_source = row.get("translation_source")

        should_translate = (
            translate_example
            and example_sentence
            and str(example_sentence).strip()
            and (force_overwrite or not existing_translation)
        )

        if should_translate:
            try:
                example_translation, translation_source = translate_english_to_chinese(
                    str(example_sentence),
                    provider=translation_provider,
                )
            except TranslationError as exc:
                errors.append(str(exc))

        status = _status_for(uk_phonetic, us_phonetic, example_sentence, example_translation, errors)
        now = datetime.now()
        enrichment_error = "；".join(errors) if errors else (example_note or None)

        with get_connection() as conn:
            conn.execute(
                update(words).where(words.c.id == int(row["id"])).values(
                    uk_phonetic=uk_phonetic,
                    us_phonetic=us_phonetic,
                    uk_audio_url=uk_audio,
                    us_audio_url=us_audio,
                    example_sentence=example_sentence,
                    example_translation=example_translation,
                    example_source=example_source,
                    translation_source=translation_source,
                    enrichment_status=status,
                    enrichment_error=enrichment_error,
                    enrichment_attempts=int(row.get("enrichment_attempts") or 0) + 1,
                    last_enriched_at=now,
                )
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
                "例句": example_sentence or "",
                "备注/错误": enrichment_error or "",
            }
        )

    return {
        "processed": total,
        "completed": success_count,
        "partial": partial_count,
        "failed": failed_count,
        "generated_examples": generated_count,
        "dictionary_examples": dictionary_example_count,
        "items": results,
    }
