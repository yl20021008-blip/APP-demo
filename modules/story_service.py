from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from textwrap import shorten
import re

from sqlalchemy import delete, func, insert, select

from modules.database import get_connection, init_database, learning_status, story_group_items, story_groups, words


@dataclass
class StoryBundle:
    title_en: str
    title_zh: str
    story_en: str
    story_zh: str
    memory_tip: str
    item_sentences: list[dict]


STYLE_CONFIG = {
    "IELTS memory story": {
        "zh_scene": "雅思考场前的一天",
        "en_scene": "the day before an IELTS exam",
        "hero": "I",
        "zh_goal": "把零散单词变成一条清晰的考试路线",
        "en_goal": "turn separate words into one clear exam route",
    },
    "campus life": {
        "zh_scene": "校园图书馆和课堂之间",
        "en_scene": "between the campus library and classroom",
        "hero": "a student",
        "zh_goal": "完成一场小组汇报",
        "en_goal": "finish a group presentation",
    },
    "city walk": {
        "zh_scene": "一场城市漫步",
        "en_scene": "a city walk",
        "hero": "a young observer",
        "zh_goal": "从街道细节里发现隐藏线索",
        "en_goal": "find hidden clues in the details of the street",
    },
    "architecture journey": {
        "zh_scene": "一次建筑调研旅程",
        "en_scene": "an architectural field trip",
        "hero": "a design student",
        "zh_goal": "把空间、行为和记忆连接起来",
        "en_goal": "connect space, behaviour, and memory",
    },
    "travel diary": {
        "zh_scene": "一本旅行日记",
        "en_scene": "a travel diary",
        "hero": "a traveller",
        "zh_goal": "记录途中不断出现的关键词",
        "en_goal": "record the key words that appear along the journey",
    },
}


def _used_word_ids(user_id: int) -> set[int]:
    with get_connection() as conn:
        rows = conn.execute(select(story_group_items.c.word_id).where(story_group_items.c.user_id == int(user_id))).all()
    return {int(r[0]) for r in rows}


def count_available_story_words(user_id: int) -> int:
    init_database()
    used = _used_word_ids(user_id)
    with get_connection() as conn:
        rows = conn.execute(select(learning_status.c.word_id).where(learning_status.c.user_id == int(user_id), learning_status.c.status != 'new')).all()
    return sum(1 for r in rows if int(r[0]) not in used)


def get_next_story_words(user_id: int, limit: int = 30) -> list[dict]:
    init_database()
    used = _used_word_ids(user_id)
    with get_connection() as conn:
        rows = conn.execute(
            select(
                words.c.id, words.c.word, words.c.part_of_speech, words.c.annotation,
                words.c.chapter, words.c.example_sentence, words.c.example_translation,
                words.c.uk_phonetic, words.c.us_phonetic,
                learning_status.c.first_learned_at, learning_status.c.last_review_at,
                learning_status.c.mastery_level,
            )
            .join(learning_status, learning_status.c.word_id == words.c.id)
            .where(learning_status.c.user_id == int(user_id), learning_status.c.status != 'new')
            .order_by(learning_status.c.first_learned_at, learning_status.c.last_review_at, words.c.chapter, words.c.original_number, words.c.id)
        ).mappings().all()
    selected = [dict(r) for r in rows if int(r['id']) not in used]
    return selected[:int(limit)]


def _clean_meaning(text: str | None, max_len: int = 24) -> str:
    if not text:
        return "关键词"
    one_line = str(text).replace("\n", "；").replace("\r", "；").strip()
    one_line = re.sub(r"\s+", " ", one_line)
    return shorten(one_line, width=max_len, placeholder="…")


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


def _use_word_in_sentence(word: str, pos: str, scene: str, meaning: str, idx: int) -> tuple[str, str]:
    connectors_en = [
        "At first", "Soon after that", "At the next stop", "While taking notes",
        "During the discussion", "Near the end", "Before leaving",
    ]
    connectors_zh = [
        "一开始", "随后", "到达下一站时", "记笔记的时候",
        "讨论过程中", "接近尾声时", "离开之前",
    ]
    ce = connectors_en[idx % len(connectors_en)]
    cz = connectors_zh[idx % len(connectors_zh)]

    if pos == "verb":
        en = f"{ce}, the guide asked us to **{word}** one important clue in {scene}, so the whole route became easier to understand."
        zh = f"{cz}，向导让我们 **{word}** 一个重要线索，这个词可以记成“{meaning}”，于是整条路线变得更清楚。"
    elif pos == "adj":
        en = f"{ce}, a more **{word}** detail appeared in {scene}, and it changed the way we interpreted the situation."
        zh = f"{cz}，场景里出现了一个更 **{word}** 的细节；我把它和“{meaning}”联系起来理解。"
    elif pos == "adv":
        en = f"{ce}, everyone moved **{word}**, trying to keep the memory route clear before the next clue disappeared."
        zh = f"{cz}，大家 **{word}** 地行动；我用“{meaning}”来固定这个词的感觉。"
    elif pos == "noun":
        article = "an" if word[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
        en = f"{ce}, we found {article} **{word}** in {scene}, and it became the symbol for the idea of {meaning}."
        zh = f"{cz}，我们在场景中发现了 **{word}**；它成为“{meaning}”这个意思的记忆符号。"
    else:
        en = f"{ce}, the word **{word}** appeared as a clue in {scene}, helping us connect the scene with the idea of {meaning}."
        zh = f"{cz}，**{word}** 作为线索出现；我把它和“{meaning}”连接起来记。"
    return en, zh


def _split_chunks(words_: list[dict], chunk_size: int = 6) -> list[list[dict]]:
    return [words_[i:i + chunk_size] for i in range(0, len(words_), chunk_size)]


def build_local_story(words_: list[dict], style: str = "IELTS memory story", intensity: str = "强化叙事版") -> StoryBundle:
    if not words_:
        raise ValueError("没有可生成故事的单词。")

    cfg = STYLE_CONFIG.get(style, STYLE_CONFIG["IELTS memory story"])
    group_size = len(words_)
    first_word = str(words_[0]["word"]).strip()
    last_word = str(words_[-1]["word"]).strip()

    title_en = f"Memory Route: {first_word} to {last_word}"
    title_zh = f"{group_size}词记忆故事：从 {first_word} 到 {last_word}"

    chapters = [str(w.get("chapter") or "未分组") for w in words_]
    chapter_hint = "、".join(dict.fromkeys(chapters[:4]))

    en_parts = [
        f"In {cfg['en_scene']}, {cfg['hero']} had one task: to {cfg['en_goal']}. "
        f"The words did not appear as a plain list. They appeared as clues along a route, "
        f"so each clue had to be collected in order."
    ]
    zh_parts = [
        f"在{cfg['zh_scene']}，主角的任务是：{cfg['zh_goal']}。"
        f"这些词不是一张普通清单，而是沿途出现的线索；只有按顺序收集，记忆路线才会完整。"
    ]

    item_sentences: list[dict] = []
    scene_names_en = [
        "the entrance", "a bright corridor", "a quiet room", "a crowded square",
        "a map wall", "a small bridge", "the final desk"
    ]
    scene_names_zh = [
        "入口处", "明亮走廊", "安静房间", "拥挤广场",
        "地图墙前", "小桥边", "最后一张桌子前"
    ]

    for chunk_idx, chunk in enumerate(_split_chunks(words_, chunk_size=6), start=1):
        en_parts.append(f"### Scene {chunk_idx}: {scene_names_en[(chunk_idx - 1) % len(scene_names_en)].title()}")
        zh_parts.append(f"### 场景 {chunk_idx}：{scene_names_zh[(chunk_idx - 1) % len(scene_names_zh)]}")

        bridge_en = (
            "The scene opened like a short film: one object, one action, and one feeling "
            "were linked together, making the next words easier to remember."
        )
        bridge_zh = "这个场景像一段短片一样展开：一个物件、一个动作、一种感受被连在一起，后面的词因此更容易记住。"
        en_parts.append(bridge_en)
        zh_parts.append(bridge_zh)

        for local_idx, item in enumerate(chunk):
            idx = (chunk_idx - 1) * 6 + local_idx
            word = str(item["word"]).strip()
            meaning = _clean_meaning(item.get("annotation"))
            pos = _detect_pos(item.get("part_of_speech"), item.get("annotation"))
            scene_en = scene_names_en[(chunk_idx - 1) % len(scene_names_en)]
            sentence_en, sentence_zh = _use_word_in_sentence(word, pos, scene_en, meaning, idx)

            en_parts.append(sentence_en)
            zh_parts.append(sentence_zh)
            item_sentences.append({
                "word_id": int(item["id"]),
                "word": word,
                "position": idx + 1,
                "sentence_en": sentence_en,
                "sentence_zh": sentence_zh,
            })

    review_words = [str(w["word"]).strip() for w in words_[:min(8, group_size)]]
    en_parts.append(
        "At the end of the route, the clues formed a chain rather than a list. "
        "To review the story, walk through the scenes again and say the highlighted words before checking their meanings."
    )
    zh_parts.append(
        "故事结束时，所有线索不再是孤立词表，而是一条连续路线。"
        "复习时先闭眼走一遍场景，再按顺序说出加粗单词，最后核对释义。"
    )

    quiz_lines = [
        "### 复习小测",
        "1. 不看词表，回忆每个场景里出现了哪些加粗词。",
        f"2. 先默写前 {len(review_words)} 个词：{', '.join(review_words)}。",
        "3. 随机选3个词，用自己的话造句。",
        f"4. 章节线索：{chapter_hint}。",
    ]
    memory_tip = "\n".join(quiz_lines)

    return StoryBundle(
        title_en=title_en,
        title_zh=title_zh,
        story_en="\n\n".join(en_parts),
        story_zh="\n\n".join(zh_parts),
        memory_tip=memory_tip,
        item_sentences=item_sentences,
    )


def _next_group_number(user_id: int) -> int:
    with get_connection() as conn:
        n = conn.execute(select(func.max(story_groups.c.group_number)).where(story_groups.c.user_id == int(user_id))).scalar()
    return int(n or 0) + 1


def create_next_story(user_id: int, group_size: int = 30, allow_partial: bool = False, style: str = "IELTS memory story", intensity: str = "强化叙事版") -> dict:
    init_database()
    selected_words = get_next_story_words(user_id, group_size)
    if len(selected_words) < group_size and not allow_partial:
        return {'created': False, 'reason': f'目前只有 {len(selected_words)} 个已学习且未进入故事的词，未满 {group_size} 个。', 'available_count': len(selected_words)}
    if not selected_words:
        return {'created': False, 'reason': '没有可生成故事的已学习单词。', 'available_count': 0}

    bundle = build_local_story(selected_words, style=style, intensity=intensity)
    group_number = _next_group_number(user_id)
    now = datetime.now()
    with get_connection() as conn:
        result = conn.execute(insert(story_groups).values(
            user_id=int(user_id),
            group_number=group_number,
            title_en=bundle.title_en,
            title_zh=bundle.title_zh,
            story_en=bundle.story_en,
            story_zh=bundle.story_zh,
            memory_tip=bundle.memory_tip,
            style=f"{style} / {intensity}",
            provider='local_narrative_v1_3',
            word_count=len(selected_words),
            created_at=now,
        ))
        story_group_id = result.inserted_primary_key[0]
        for item in bundle.item_sentences:
            conn.execute(insert(story_group_items).values(
                user_id=int(user_id),
                story_group_id=int(story_group_id),
                word_id=int(item['word_id']),
                position=int(item['position']),
                sentence_en=item['sentence_en'],
                sentence_zh=item['sentence_zh'],
            ))

    return {
        'created': True,
        'story_group_id': int(story_group_id),
        'group_number': group_number,
        'word_count': len(selected_words),
        'title_zh': bundle.title_zh,
        'title_en': bundle.title_en,
    }


def list_stories(user_id: int) -> list[dict]:
    init_database()
    with get_connection() as conn:
        rows = conn.execute(
            select(story_groups.c.id, story_groups.c.group_number, story_groups.c.title_zh, story_groups.c.title_en, story_groups.c.word_count, story_groups.c.provider, story_groups.c.created_at)
            .where(story_groups.c.user_id == int(user_id))
            .order_by(story_groups.c.group_number.desc())
        ).mappings().all()
    return [dict(r) for r in rows]


def get_story_detail(user_id: int, story_group_id: int) -> dict | None:
    init_database()
    with get_connection() as conn:
        story = conn.execute(select(story_groups).where(story_groups.c.user_id == int(user_id), story_groups.c.id == int(story_group_id))).mappings().first()
        if story is None:
            return None
        item_rows = conn.execute(
            select(
                story_group_items.c.position, words.c.word, words.c.part_of_speech, words.c.annotation,
                words.c.uk_phonetic, words.c.us_phonetic, story_group_items.c.sentence_en, story_group_items.c.sentence_zh,
            )
            .join(words, words.c.id == story_group_items.c.word_id)
            .where(story_group_items.c.user_id == int(user_id), story_group_items.c.story_group_id == int(story_group_id))
            .order_by(story_group_items.c.position)
        ).mappings().all()
    return {'story': dict(story), 'items': [dict(r) for r in item_rows]}


def delete_story(user_id: int, story_group_id: int) -> None:
    init_database()
    with get_connection() as conn:
        conn.execute(delete(story_groups).where(story_groups.c.user_id == int(user_id), story_groups.c.id == int(story_group_id)))
