from __future__ import annotations

from dataclasses import asdict, dataclass
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
    session.headers.update(
        {"User-Agent": "IELTS-Vocabulary-Planner/0.3.1"}
    )
    return session


def _normalize_audio_url(url: str | None) -> str | None:
    if not url:
        return None
    if url.startswith("//"):
        return f"https:{url}"
    return url


def _first_example(entry: dict[str, Any]) -> str | None:
    for meaning in entry.get("meanings") or []:
        for definition in meaning.get("definitions") or []:
            example = definition.get("example")
            if isinstance(example, str) and example.strip():
                return example.strip()
    return None


def lookup_word(word: str, timeout: float = 10.0) -> DictionaryResult:
    clean_word = word.strip().lower()
    if not clean_word:
        raise DictionaryLookupError("单词为空。")

    session = _build_session()

    try:
        response = session.get(
            API_URL.format(word=clean_word),
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise DictionaryLookupError(f"词典请求失败：{exc}") from exc

    if response.status_code == 404:
        raise DictionaryLookupError("词典没有找到该词。")
    if response.status_code != 200:
        raise DictionaryLookupError(
            f"词典返回 HTTP {response.status_code}。"
        )

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

    # 先按音频文件名识别英式/美式，再用默认音标兜底。
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

    # 某些词只有一个音标或无法从音频名判断口音。
    all_texts = [
        item.get("text")
        for item in phonetics
        if isinstance(item, dict) and item.get("text")
    ]
    fallback_text = default_phonetic or (all_texts[0] if all_texts else None)

    result.uk_phonetic = result.uk_phonetic or fallback_text
    result.us_phonetic = result.us_phonetic or fallback_text
    result.example_sentence = _first_example(entry)

    return result
