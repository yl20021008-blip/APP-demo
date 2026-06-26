from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from textwrap import shorten

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
            select(words.c.id, words.c.word, words.c.part_of_speech, words.c.annotation, words.c.chapter,
                   words.c.example_sentence, words.c.example_translation, learning_status.c.first_learned_at,
                   learning_status.c.last_review_at)
            .select_from(learning_status.join(words, learning_status.c.word_id == words.c.id))
            .where(learning_status.c.user_id == int(user_id), learning_status.c.status != 'new')
            .order_by(learning_status.c.first_learned_at.asc().nulls_last(), learning_status.c.last_review_at.asc().nulls_last(), words.c.chapter, words.c.original_number, words.c.id)
        ).mappings().all()
    selected = [dict(r) for r in rows if int(r['id']) not in used]
    return selected[:int(limit)]


def _clean_meaning(text: str | None, max_len: int = 22) -> str:
    if not text:
        return '相关概念'
    one_line = str(text).replace('\n', '；').replace('\r', '；').strip()
    return shorten(one_line, width=max_len, placeholder='…')


def build_local_story(words_list: list[dict], style: str = 'IELTS memory story') -> StoryBundle:
    if not words_list:
        raise ValueError('没有可生成故事的单词。')
    scenes = ['a quiet IELTS study street', 'an old city gate', 'a bright library corridor', 'a small riverside classroom', 'a morning market near campus', 'a museum of future cities']
    scenes_zh = ['一条安静的雅思学习街道', '一座旧城门', '一条明亮的图书馆走廊', '一间河边小教室', '校园附近的清晨集市', '一座未来城市博物馆']
    title_en = f'Memory Walk #{datetime.now().strftime("%m%d")} with {len(words_list)} Words'
    title_zh = f'{len(words_list)}词记忆小故事：一场记忆漫步'
    en_parts = ['Before my IELTS exam, I entered a strange memory city. Every corner hid one vocabulary clue.']
    zh_parts = ['雅思考试前，我走进一座奇妙的记忆城市。城市的每一个角落都藏着一个单词线索。']
    item_sentences = []
    for idx, item in enumerate(words_list):
        word = str(item['word']).strip()
        meaning = _clean_meaning(item.get('annotation'))
        sentence_en = f'At {scenes[idx % len(scenes)]}, I found **{word}**, and connected it with {meaning}.'
        sentence_zh = f'在{scenes_zh[idx % len(scenes_zh)]}，我遇到 **{word}**，并把它和“{meaning}”联系起来。'
        en_parts.append(sentence_en)
        zh_parts.append(sentence_zh)
        item_sentences.append({'word_id': int(item['id']), 'word': word, 'position': idx + 1, 'sentence_en': sentence_en, 'sentence_zh': sentence_zh})
    en_parts.append('When the last clue was found, the words became one clear route in my mind.')
    zh_parts.append('当最后一个线索被找到时，这些词在我的脑海里变成了一条清晰路线。')
    return StoryBundle(title_en, title_zh, '\n\n'.join(en_parts), '\n\n'.join(zh_parts), '复习时先回忆故事路线，再按故事顺序说出目标词。', item_sentences)


def _next_group_number(user_id: int) -> int:
    with get_connection() as conn:
        number = conn.execute(select(func.max(story_groups.c.group_number)).where(story_groups.c.user_id == int(user_id))).scalar()
    return int(number or 0) + 1


def create_next_story(user_id: int, group_size: int = 30, allow_partial: bool = False, style: str = 'IELTS memory story') -> dict:
    init_database()
    words_list = get_next_story_words(user_id, group_size)
    if len(words_list) < group_size and not allow_partial:
        return {'created': False, 'reason': f'目前只有 {len(words_list)} 个已学习且未进入故事的词，未满 {group_size} 个。', 'available_count': len(words_list)}
    if not words_list:
        return {'created': False, 'reason': '没有可生成故事的已学习单词。', 'available_count': 0}
    bundle = build_local_story(words_list, style=style)
    group_number = _next_group_number(user_id)
    with get_connection() as conn:
        result = conn.execute(insert(story_groups).values(user_id=int(user_id), group_number=group_number, title_en=bundle.title_en, title_zh=bundle.title_zh, story_en=bundle.story_en, story_zh=bundle.story_zh, memory_tip=bundle.memory_tip, style=style, provider='local_template', word_count=len(words_list), created_at=datetime.now()))
        story_group_id = int(result.inserted_primary_key[0])
        conn.execute(insert(story_group_items), [{'user_id': int(user_id), 'story_group_id': story_group_id, 'word_id': item['word_id'], 'position': item['position'], 'sentence_en': item['sentence_en'], 'sentence_zh': item['sentence_zh']} for item in bundle.item_sentences])
    return {'created': True, 'story_group_id': story_group_id, 'group_number': group_number, 'word_count': len(words_list), 'title_zh': bundle.title_zh, 'title_en': bundle.title_en}


def list_stories(user_id: int) -> list[dict]:
    init_database()
    with get_connection() as conn:
        rows = conn.execute(select(story_groups.c.id, story_groups.c.group_number, story_groups.c.title_zh, story_groups.c.title_en, story_groups.c.word_count, story_groups.c.provider, story_groups.c.created_at).where(story_groups.c.user_id == int(user_id)).order_by(story_groups.c.group_number.desc())).mappings().all()
    return [dict(r) for r in rows]


def get_story_detail(user_id: int, story_group_id: int) -> dict | None:
    init_database()
    with get_connection() as conn:
        story = conn.execute(select(story_groups).where(story_groups.c.id == int(story_group_id), story_groups.c.user_id == int(user_id))).mappings().first()
        if story is None:
            return None
        items = conn.execute(
            select(story_group_items.c.position, words.c.word, words.c.part_of_speech, words.c.annotation, words.c.uk_phonetic, words.c.us_phonetic, story_group_items.c.sentence_en, story_group_items.c.sentence_zh)
            .select_from(story_group_items.join(words, story_group_items.c.word_id == words.c.id))
            .where(story_group_items.c.story_group_id == int(story_group_id), story_group_items.c.user_id == int(user_id))
            .order_by(story_group_items.c.position)
        ).mappings().all()
    return {'story': dict(story), 'items': [dict(i) for i in items]}


def delete_story(user_id: int, story_group_id: int) -> None:
    init_database()
    with get_connection() as conn:
        conn.execute(delete(story_groups).where(story_groups.c.id == int(story_group_id), story_groups.c.user_id == int(user_id)))
