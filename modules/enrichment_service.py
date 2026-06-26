from __future__ import annotations

import json
from datetime import datetime
from typing import Callable

from sqlalchemy import insert, select, update, func

from modules.database import enrichment_cache, get_connection, init_database, words
from modules.dictionary_provider import DictionaryLookupError, DictionaryResult, lookup_word
from modules.translation_provider import TranslationError, translate_english_to_chinese

ProgressCallback = Callable[[int, int, str], None]


def get_enrichment_summary(chapter: str | None = None) -> dict[str, int]:
    init_database()
    with get_connection() as conn:
        rows = conn.execute(select(words)).mappings().all()
    selected = [dict(r) for r in rows if not chapter or chapter == '全部' or r['chapter'] == chapter]
    return {
        'total': len(selected),
        'missing_phonetic': sum(1 for r in selected if not (r.get('uk_phonetic') or r.get('us_phonetic'))),
        'missing_example': sum(1 for r in selected if not str(r.get('example_sentence') or '').strip()),
        'missing_translation': sum(1 for r in selected if str(r.get('example_sentence') or '').strip() and not str(r.get('example_translation') or '').strip()),
        'failed': sum(1 for r in selected if r.get('enrichment_status') == 'failed'),
    }


def _load_cached_dictionary(word: str) -> DictionaryResult | None:
    with get_connection() as conn:
        row = conn.execute(select(enrichment_cache.c.payload_json).where(enrichment_cache.c.word == word.lower())).first()
    if row is None:
        return None
    try:
        return DictionaryResult(**json.loads(row[0]))
    except Exception:
        return None


def _save_dictionary_cache(result: DictionaryResult) -> None:
    now = datetime.now()
    payload = json.dumps(result.to_dict(), ensure_ascii=False)
    with get_connection() as conn:
        existing = conn.execute(select(enrichment_cache.c.word).where(enrichment_cache.c.word == result.word.lower())).first()
        if existing:
            conn.execute(update(enrichment_cache).where(enrichment_cache.c.word == result.word.lower()).values(payload_json=payload, source=result.source, fetched_at=now))
        else:
            conn.execute(insert(enrichment_cache).values(word=result.word.lower(), payload_json=payload, source=result.source, fetched_at=now))


def _get_dictionary_result(word: str, force_refresh: bool) -> DictionaryResult:
    if not force_refresh:
        cached = _load_cached_dictionary(word)
        if cached is not None:
            return cached
    result = lookup_word(word)
    _save_dictionary_cache(result)
    return result


def _select_words(chapter: str | None, limit: int, retry_failed: bool, force_overwrite: bool) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(select(words).order_by(words.c.chapter, words.c.original_number, words.c.id)).mappings().all()
    selected = []
    for r in rows:
        row = dict(r)
        if chapter and chapter != '全部' and row['chapter'] != chapter:
            continue
        if retry_failed and row.get('enrichment_status') != 'failed':
            continue
        if not retry_failed and not force_overwrite:
            missing = (
                not (row.get('uk_phonetic') or row.get('us_phonetic'))
                or not str(row.get('example_sentence') or '').strip()
                or (str(row.get('example_sentence') or '').strip() and not str(row.get('example_translation') or '').strip())
                or row.get('enrichment_status') in {'pending', 'partial'}
            )
            if not missing:
                continue
        selected.append(row)
        if len(selected) >= int(limit):
            break
    return selected


def _status_for(uk_phonetic, us_phonetic, example_sentence, example_translation, errors: list[str]) -> str:
    has_phonetic = bool(uk_phonetic or us_phonetic)
    has_example = bool(example_sentence and str(example_sentence).strip())
    has_translation = bool(example_translation and str(example_translation).strip())
    if has_phonetic and has_example and has_translation and not errors:
        return 'completed'
    if has_phonetic or has_example or has_translation:
        return 'partial'
    return 'failed'


def enrich_words(chapter: str | None = None, limit: int = 10, fill_missing_example: bool = True,
                 translate_example: bool = True, retry_failed: bool = False, force_overwrite: bool = False,
                 translation_provider: str | None = None, progress_callback: ProgressCallback | None = None) -> dict:
    init_database()
    rows = _select_words(chapter, max(1, int(limit)), retry_failed, force_overwrite)
    results = []
    counts = {'completed': 0, 'partial': 0, 'failed': 0}
    total = len(rows)
    for index, row in enumerate(rows, start=1):
        word = str(row.get('word') or '').strip()
        if progress_callback:
            progress_callback(index, total, word)
        errors = []
        dictionary_result = None
        try:
            dictionary_result = _get_dictionary_result(word, force_refresh=force_overwrite)
        except DictionaryLookupError as exc:
            errors.append(str(exc))

        uk_phonetic = row.get('uk_phonetic')
        us_phonetic = row.get('us_phonetic')
        uk_audio = row.get('uk_audio_url')
        us_audio = row.get('us_audio_url')
        if dictionary_result:
            uk_phonetic = dictionary_result.uk_phonetic if force_overwrite or not uk_phonetic else uk_phonetic
            us_phonetic = dictionary_result.us_phonetic if force_overwrite or not us_phonetic else us_phonetic
            uk_audio = dictionary_result.uk_audio_url if force_overwrite or not uk_audio else uk_audio
            us_audio = dictionary_result.us_audio_url if force_overwrite or not us_audio else us_audio

        example_sentence = row.get('example_sentence')
        example_source = row.get('example_source') or ('雅思词库导入' if example_sentence else None)
        if (not example_sentence or not str(example_sentence).strip()) and fill_missing_example and dictionary_result:
            example_sentence = dictionary_result.example_sentence
            if example_sentence:
                example_source = dictionary_result.source

        example_translation = row.get('example_translation')
        translation_source = row.get('translation_source')
        if translate_example and example_sentence and (force_overwrite or not example_translation):
            try:
                example_translation, translation_source = translate_english_to_chinese(str(example_sentence), provider=translation_provider)
            except TranslationError as exc:
                errors.append(str(exc))

        status = _status_for(uk_phonetic, us_phonetic, example_sentence, example_translation, errors)
        counts[status] += 1
        with get_connection() as conn:
            conn.execute(update(words).where(words.c.id == int(row['id'])).values(
                uk_phonetic=uk_phonetic, us_phonetic=us_phonetic,
                uk_audio_url=uk_audio, us_audio_url=us_audio,
                example_sentence=example_sentence, example_translation=example_translation,
                example_source=example_source, translation_source=translation_source,
                enrichment_status=status, enrichment_error='；'.join(errors) if errors else None,
                enrichment_attempts=int(row.get('enrichment_attempts') or 0) + 1,
                last_enriched_at=datetime.now(),
            ))
        results.append({'单词': word, '状态': status, '英式音标': uk_phonetic or '', '美式音标': us_phonetic or '', '例句来源': example_source or '', '翻译来源': translation_source or '', '错误': '；'.join(errors)})
    return {'processed': total, 'completed': counts['completed'], 'partial': counts['partial'], 'failed': counts['failed'], 'items': results}
