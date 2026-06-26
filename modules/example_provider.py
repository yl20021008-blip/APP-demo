from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedExample:
    sentence: str
    source: str
    quality_note: str


def _clean_text(value: object | None, max_len: int = 90) -> str:
    if value is None:
        return ""
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "…"


def _detect_pos(part_of_speech: str | None, annotation: str | None) -> str:
    text = f"{part_of_speech or ''} {annotation or ''}".lower()
    if any(token in text for token in ["adv", "副词"]):
        return "adv"
    if any(token in text for token in ["adj", "形容词"]):
        return "adj"
    if any(token in text for token in ["verb", " v.", "v.", "动词"]):
        return "verb"
    if any(token in text for token in ["noun", " n.", "n.", "名词"]):
        return "noun"
    return "general"


def _article_for(word: str) -> str:
    return "an" if word[:1].lower() in {"a", "e", "i", "o", "u"} else "a"


def build_generated_example(
    word: str,
    part_of_speech: str | None = None,
    annotation: str | None = None,
    chapter: str | None = None,
    style: str = "ielts",
) -> GeneratedExample:
    """生成一个适合背词的英文例句。

    这不是权威词典例句，而是学习用 fallback：
    当词典 API 没有例句时，保证页面仍然有可读、可翻译、可记忆的例句。
    """
    clean_word = str(word or "").strip().lower()
    if not clean_word:
        raise ValueError("word is empty")

    meaning = _clean_text(annotation, max_len=80)
    topic = _clean_text(chapter, max_len=40) or "academic study"
    pos = _detect_pos(part_of_speech, annotation)

    # 这里避免生硬地把中文释义塞进英文句子，只用释义帮助选择句式。
    if style == "daily":
        templates = {
            "noun": [
                "I noticed {article} {word} during our discussion about {topic}.",
                "The teacher used {article} {word} to make the idea easier to understand.",
            ],
            "verb": [
                "We need to {word} the problem before we choose a solution.",
                "Students often try to {word} new information with what they already know.",
            ],
            "adj": [
                "The situation became more {word} after we looked at the details.",
                "A {word} example can help students remember a difficult idea.",
            ],
            "adv": [
                "The group worked {word} to finish the task before the deadline.",
                "She explained the answer {word}, so everyone could follow it.",
            ],
            "general": [
                "I wrote down the word {word} because it appeared in an important paragraph.",
                "In class, {word} became the key word for understanding the whole text.",
            ],
        }
    else:
        templates = {
            "noun": [
                "The recent report identifies {article} {word} as an important factor in the discussion of {topic}.",
                "Researchers often examine {article} {word} when they analyse changes in society, education, or the environment.",
            ],
            "verb": [
                "Policymakers need to {word} the available evidence before they introduce a new strategy.",
                "Researchers try to {word} different sources of data before drawing a reliable conclusion.",
            ],
            "adj": [
                "A more {word} approach may help students understand complex academic texts.",
                "The results became more {word} when the researchers compared several groups of participants.",
            ],
            "adv": [
                "The team analysed the survey data {word} before presenting the final conclusion.",
                "The speaker explained the argument {word}, which made the lecture easier to follow.",
            ],
            "general": [
                "In IELTS reading, the word {word} often helps reveal the main idea of a paragraph.",
                "The word {word} can be useful when describing causes, effects, or changes in an academic context.",
            ],
        }

    idx = (sum(ord(ch) for ch in clean_word) + len(topic)) % len(templates[pos])
    sentence = templates[pos][idx].format(
        word=clean_word,
        article=_article_for(clean_word),
        topic=topic,
    )

    if meaning:
        note = f"本句为学习生成例句；目标词释义参考：{meaning}"
    else:
        note = "本句为学习生成例句；建议后续用词典例句替换。"

    return GeneratedExample(
        sentence=sentence,
        source="local_generated_ielts_example",
        quality_note=note,
    )
