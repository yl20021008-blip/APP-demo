from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from textwrap import shorten

from modules.database import get_connection, init_database


@dataclass
class StoryBundle:
    title_en: str
    title_zh: str
    story_en: str
    story_zh: str
    memory_tip: str
    item_sentences: list[dict]


def count_available_story_words() -> int:
    init_database()
    with get_connection() as connection:
        count = connection.execute(
            """
            SELECT COUNT(*)
            FROM learning_status ls
            JOIN words w ON w.id = ls.word_id
            LEFT JOIN story_group_items sgi ON sgi.word_id = w.id
            WHERE ls.status != 'new'
              AND sgi.word_id IS NULL
            """
        ).fetchone()[0]
    return int(count)


def get_next_story_words(limit: int = 30) -> list[dict]:
    init_database()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                w.id,
                w.word,
                w.part_of_speech,
                w.annotation,
                w.chapter,
                w.example_sentence,
                w.example_translation,
                ls.first_learned_at,
                ls.last_review_at
            FROM learning_status ls
            JOIN words w ON w.id = ls.word_id
            LEFT JOIN story_group_items sgi ON sgi.word_id = w.id
            WHERE ls.status != 'new'
              AND sgi.word_id IS NULL
            ORDER BY
                COALESCE(ls.first_learned_at, ls.last_review_at),
                w.chapter,
                COALESCE(w.original_number, 999999),
                w.id
            LIMIT ?
            """,
            (int(limit),),
        ).fetchall()
    return [dict(row) for row in rows]


def _clean_meaning(text: str | None, max_len: int = 22) -> str:
    if not text:
        return "相关概念"
    one_line = str(text).replace("\n", "；").replace("\r", "；").strip()
    return shorten(one_line, width=max_len, placeholder="…")


def _make_sentence_en(index: int, word: str, meaning: str, scene: str) -> str:
    templates = [
        "At {scene}, I noticed **{word}**, a clue that reminded me of {meaning}.",
        "Then my guide pointed to **{word}**, explaining it as {meaning}.",
        "I wrote **{word}** in my notebook because it connected with {meaning}.",
        "A small sign appeared: **{word}**, which helped me remember {meaning}.",
        "Before moving on, I repeated **{word}** and linked it to {meaning}.",
    ]
    return templates[index % len(templates)].format(scene=scene, word=word, meaning=meaning)


def _make_sentence_zh(index: int, word: str, meaning: str, scene: str) -> str:
    templates = [
        "在{scene}，我注意到 **{word}**，它让我想到“{meaning}”。",
        "随后向导指着 **{word}**，解释它和“{meaning}”有关。",
        "我把 **{word}** 写进笔记本，因为它能帮助我记住“{meaning}”。",
        "一个小标志出现了：**{word}**，它对应着“{meaning}”。",
        "离开前，我默念 **{word}**，并把它和“{meaning}”连在一起。",
    ]
    return templates[index % len(templates)].format(scene=scene, word=word, meaning=meaning)


def build_local_story(words: list[dict], style: str = "IELTS memory story") -> StoryBundle:
    if not words:
        raise ValueError("没有可生成故事的单词。")

    scenes = [
        "a quiet IELTS study street",
        "an old city gate",
        "a bright library corridor",
        "a small riverside classroom",
        "a morning market near campus",
        "a museum of future cities",
    ]
    scenes_zh = [
        "一条安静的雅思学习街道",
        "一座旧城门",
        "一条明亮的图书馆走廊",
        "一间河边小教室",
        "校园附近的清晨集市",
        "一座未来城市博物馆",
    ]

    title_en = f"Memory Walk #{datetime.now().strftime('%m%d')} with {len(words)} Words"
    title_zh = f"{len(words)}词记忆小故事：一场记忆漫步"

    en_parts = [
        "Before my IELTS exam, I entered a strange memory city. "
        "Every corner hid one vocabulary clue, and I had to collect them in order."
    ]
    zh_parts = [
        "雅思考试前，我走进一座奇妙的记忆城市。"
        "城市的每一个角落都藏着一个单词线索，我必须按顺序收集它们。"
    ]
    item_sentences = []

    for idx, item in enumerate(words):
        word = str(item["word"]).strip()
        meaning = _clean_meaning(item.get("annotation"))
        scene = scenes[idx % len(scenes)]
        scene_zh = scenes_zh[idx % len(scenes_zh)]

        sentence_en = _make_sentence_en(idx, word, meaning, scene)
        sentence_zh = _make_sentence_zh(idx, word, meaning, scene_zh)

        en_parts.append(sentence_en)
        zh_parts.append(sentence_zh)
        item_sentences.append(
            {
                "word_id": int(item["id"]),
                "word": word,
                "position": idx + 1,
                "sentence_en": sentence_en,
                "sentence_zh": sentence_zh,
            }
        )

    en_parts.append(
        "When the last clue was found, the city turned into a clear map in my mind. "
        "The words were no longer separate cards; they had become one route."
    )
    zh_parts.append(
        "当最后一个线索被找到时，这座城市在我的脑海里变成了一张清晰的地图。"
        "这些词不再是一张张孤立的卡片，而是一条完整路线。"
    )

    memory_tip = "复习时先回忆故事路线，再按故事顺序说出目标词；卡住时回到对应单词卡片。"

    return StoryBundle(
        title_en=title_en,
        title_zh=title_zh,
        story_en="\n\n".join(en_parts),
        story_zh="\n\n".join(zh_parts),
        memory_tip=memory_tip,
        item_sentences=item_sentences,
    )


def _next_group_number() -> int:
    with get_connection() as connection:
        row = connection.execute("SELECT COALESCE(MAX(group_number), 0) + 1 FROM story_groups").fetchone()
    return int(row[0])


def create_next_story(group_size: int = 30, allow_partial: bool = False, style: str = "IELTS memory story") -> dict:
    init_database()
    words = get_next_story_words(group_size)

    if len(words) < group_size and not allow_partial:
        return {
            "created": False,
            "reason": f"目前只有 {len(words)} 个已学习且未进入故事的词，未满 {group_size} 个。",
            "available_count": len(words),
        }

    if not words:
        return {
            "created": False,
            "reason": "没有可生成故事的已学习单词。",
            "available_count": 0,
        }

    bundle = build_local_story(words, style=style)
    group_number = _next_group_number()

    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO story_groups(
                group_number, title_en, title_zh, story_en, story_zh,
                memory_tip, style, provider, word_count, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                group_number,
                bundle.title_en,
                bundle.title_zh,
                bundle.story_en,
                bundle.story_zh,
                bundle.memory_tip,
                style,
                "local_template",
                len(words),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        story_group_id = cursor.lastrowid

        for item in bundle.item_sentences:
            connection.execute(
                """
                INSERT INTO story_group_items(
                    story_group_id, word_id, position, sentence_en, sentence_zh
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    story_group_id,
                    item["word_id"],
                    item["position"],
                    item["sentence_en"],
                    item["sentence_zh"],
                ),
            )

    return {
        "created": True,
        "story_group_id": story_group_id,
        "group_number": group_number,
        "word_count": len(words),
        "title_zh": bundle.title_zh,
        "title_en": bundle.title_en,
    }


def list_stories() -> list[dict]:
    init_database()
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, group_number, title_zh, title_en, word_count, provider, created_at
            FROM story_groups
            ORDER BY group_number DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_story_detail(story_group_id: int) -> dict | None:
    init_database()
    with get_connection() as connection:
        story = connection.execute("SELECT * FROM story_groups WHERE id = ?", (int(story_group_id),)).fetchone()
        if story is None:
            return None

        items = connection.execute(
            """
            SELECT
                sgi.position,
                w.word,
                w.part_of_speech,
                w.annotation,
                w.uk_phonetic,
                w.us_phonetic,
                sgi.sentence_en,
                sgi.sentence_zh
            FROM story_group_items sgi
            JOIN words w ON w.id = sgi.word_id
            WHERE sgi.story_group_id = ?
            ORDER BY sgi.position
            """,
            (int(story_group_id),),
        ).fetchall()

    return {"story": dict(story), "items": [dict(item) for item in items]}


def delete_story(story_group_id: int) -> None:
    init_database()
    with get_connection() as connection:
        connection.execute("DELETE FROM story_groups WHERE id = ?", (int(story_group_id),))
