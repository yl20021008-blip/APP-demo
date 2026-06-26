from __future__ import annotations

import html
import os

import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()


class TranslationError(RuntimeError):
    pass


def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "POST"}),
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update(
        {"User-Agent": "IELTS-Vocabulary-Planner/0.3.1"}
    )
    return session


def _translate_mymemory(text: str, timeout: float) -> tuple[str, str]:
    encoded_length = len(text.encode("utf-8"))
    if encoded_length > 500:
        raise TranslationError(
            "MyMemory 单次文本上限为500字节；当前例句过长。"
        )

    params = {
        "q": text,
        "langpair": "en|zh-CN",
        "mt": "1",
    }
    email = os.getenv("MYMEMORY_EMAIL", "").strip()
    if email:
        params["de"] = email

    session = _build_session()
    try:
        response = session.get(
            "https://api.mymemory.translated.net/get",
            params=params,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise TranslationError(f"MyMemory 请求失败：{exc}") from exc

    if response.status_code != 200:
        raise TranslationError(
            f"MyMemory 返回 HTTP {response.status_code}。"
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise TranslationError("MyMemory 返回内容不是有效 JSON。") from exc

    translated = (
        payload.get("responseData", {}).get("translatedText")
        if isinstance(payload, dict)
        else None
    )
    if not isinstance(translated, str) or not translated.strip():
        raise TranslationError("MyMemory 没有返回有效翻译。")

    translated = html.unescape(translated).strip()
    if "MYMEMORY WARNING" in translated.upper():
        raise TranslationError(translated)
    if translated.casefold() == text.strip().casefold():
        raise TranslationError("翻译结果与英文原文相同。")

    return translated, "MyMemory"


def _translate_deepl(text: str, timeout: float) -> tuple[str, str]:
    api_key = os.getenv("DEEPL_API_KEY", "").strip()
    if not api_key:
        raise TranslationError("没有配置 DEEPL_API_KEY。")

    use_free = os.getenv("DEEPL_USE_FREE", "true").strip().lower() not in {
        "0",
        "false",
        "no",
    }
    endpoint = (
        "https://api-free.deepl.com/v2/translate"
        if use_free
        else "https://api.deepl.com/v2/translate"
    )

    session = _build_session()
    headers = {
        "Authorization": f"DeepL-Auth-Key {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": [text],
        "source_lang": "EN",
        "target_lang": "ZH",
    }

    try:
        response = session.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise TranslationError(f"DeepL 请求失败：{exc}") from exc

    if response.status_code != 200:
        raise TranslationError(
            f"DeepL 返回 HTTP {response.status_code}："
            f"{response.text[:200]}"
        )

    try:
        data = response.json()
        translated = data["translations"][0]["text"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise TranslationError("DeepL 返回结构异常。") from exc

    if not translated or not translated.strip():
        raise TranslationError("DeepL 没有返回有效翻译。")

    return translated.strip(), "DeepL"


def translate_english_to_chinese(
    text: str,
    provider: str | None = None,
    timeout: float = 15.0,
) -> tuple[str, str]:
    clean_text = text.strip()
    if not clean_text:
        raise TranslationError("待翻译文本为空。")

    selected = (
        provider
        or os.getenv("TRANSLATION_PROVIDER", "mymemory")
    ).strip().lower()

    if selected == "mymemory":
        return _translate_mymemory(clean_text, timeout)
    if selected == "deepl":
        return _translate_deepl(clean_text, timeout)
    if selected in {"none", "off", "disabled"}:
        raise TranslationError("翻译功能已关闭。")

    raise TranslationError(
        f"未知翻译服务：{selected}。可选 mymemory 或 deepl。"
    )
