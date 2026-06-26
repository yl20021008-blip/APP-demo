from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://api.dictionaryapi.dev/api/v2/entries/en/{word}"


class DictionaryLookupError(RuntimeError):
    pass


@dataclass
class DictionaryResult:
    word: str
    uk_phonetic: str | None = None
    us_phonetic: str | None = None
    uk_audio_url: str | None = None
    us_audio_url: str | None = None
    example_sentence: str | None = None
    example_candidates: list[str] = field(default_factory=list)
    source: str = "dictionaryapi.dev"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.4,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "IELTS-Vocabulary-Planner/1.3"})
    return session


def _normalize_audio_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _collect_examples(entry: dict[str, Any], limit: int = 5) -> list[str]:
    examples: list[str] = []
    seen: set[str] = set()
    for meaning in entry.get("meanings") or []:
        for definition in meaning.get("definitions") or []:
            example = definition.get("example")
            if isinstance(example, str):
                clean = " ".join(example.strip().split())
                if clean and clean.lower() not in seen:
                    examples.append(clean)
                    seen.add(clean.lower())
                    if len(examples) >= limit:
                        return examples
    return examples


def _score_example(word: str, sentence: str) -> tuple[int, int]:
    clean_word = word.lower()
    clean_sentence = sentence.lower()
    contains = 1 if clean_word in clean_sentence else 0
    length = len(sentence)
    # 背词例句不要过长也不要过短，优先 55-160 字符。
    if 55 <= length <= 160:
        length_score = 2
    elif 30 <= length <= 220:
        length_score = 1
    else:
        length_score = 0
    return contains + length_score, -abs(length - 100)


def _pick_best_example(word: str, examples: list[str]) -> str | None:
    if not examples:
        return None
    ranked = sorted(examples, key=lambda sentence: _score_example(word, sentence), reverse=True)
    return ranked[0]


def lookup_word(word: str, timeout: float = 10.0) -> DictionaryResult:
    clean_word = word.strip().lower()
    if not clean_word:
        raise DictionaryLookupError("单词为空。")

    session = _build_session()

    try:
        response = session.get(API_URL.format(word=clean_word), timeout=timeout)
    except requests.RequestException as exc:
        raise DictionaryLookupError(f"词典请求失败：{exc}") from exc

    if response.status_code == 404:
        raise DictionaryLookupError("词典没有找到该词。")
    if response.status_code != 200:
        raise DictionaryLookupError(f"词典返回 HTTP {response.status_code}。")

    try:
        payload = response.json()
    except ValueError as exc:
        raise DictionaryLookupError("词典返回内容不是有效 JSON。") from exc

    if not isinstance(payload, list) or not payload:
        raise DictionaryLookupError("词典返回内容为空。")

    entry = payload[0]
    if not isinstance(entry, dict):
        raise DictionaryLookupError("词典返回结构异常。")

    result = DictionaryResult(word=clean_word)
    default_phonetic = entry.get("phonetic")
    phonetics = entry.get("phonetics") or []

    for item in phonetics:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        audio = _normalize_audio_url(item.get("audio"))
        audio_lower = (audio or "").lower()

        is_uk = any(token in audio_lower for token in ("-uk.", "_uk_", "/uk/", "-gb.", "_gb_"))
        is_us = any(token in audio_lower for token in ("-us.", "_us_", "/us/"))

        if is_uk:
            result.uk_phonetic = result.uk_phonetic or text or default_phonetic
            result.uk_audio_url = result.uk_audio_url or audio
        elif is_us:
            result.us_phonetic = result.us_phonetic or text or default_phonetic
            result.us_audio_url = result.us_audio_url or audio

    all_texts = [
        item.get("text")
        for item in phonetics
        if isinstance(item, dict) and item.get("text")
    ]
    fallback_text = default_phonetic or (all_texts[0] if all_texts else None)

    result.uk_phonetic = result.uk_phonetic or fallback_text
    result.us_phonetic = result.us_phonetic or fallback_text
    result.example_candidates = _collect_examples(entry)
    result.example_sentence = _pick_best_example(clean_word, result.example_candidates)
    return result
