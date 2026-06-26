from __future__ import annotations

from datetime import datetime

from sqlalchemy import and_, insert, select, update

from modules.database import get_connection, init_database, ensure_user_word_status, learning_status, review_logs, words
from modules.review_algorithm import calculate_review


def _word_status_columns(task_type: str):
    return [
        words.c.id.label('id'), words.c.book_name, words.c.chapter, words.c.original_number,
        words.c.word, words.c.part_of_speech, words.c.annotation, words.c.expansion,
        words.c.collocation, words.c.example_sentence, words.c.uk_phonetic, words.c.us_phonetic,
        words.c.uk_audio_url, words.c.us_audio_url, words.c.example_translation,
        words.c.example_source, words.c.translation_source,
        learning_status.c.status, learning_status.c.mastery_level,
        learning_status.c.total_reviews, learning_status.c.next_review_at,
    ]


def get_today_queue(user_id: int, daily_new_limit: int, daily_review_limit: int = 200) -> list[dict]:
    init_database()
    ensure_user_word_status(int(user_id))
    now = datetime.now()
    with get_connection() as conn:
        base_join = learning_status.join(words, learning_status.c.word_id == words.c.id)
        due_rows = conn.execute(
            select(*_word_status_columns('review'))
            .select_from(base_join)
            .where(
                learning_status.c.user_id == int(user_id),
                learning_status.c.status != 'new',
                learning_status.c.next_review_at.is_not(None),
                learning_status.c.next_review_at <= now,
            )
            .order_by(learning_status.c.next_review_at.asc())
            .limit(int(daily_review_limit))
        ).mappings().all()
        new_rows = conn.execute(
            select(*_word_status_columns('new'))
            .select_from(base_join)
            .where(
                learning_status.c.user_id == int(user_id),
                learning_status.c.status == 'new',
            )
            .order_by(words.c.chapter.asc(), words.c.original_number.asc().nulls_last(), words.c.id.asc())
            .limit(int(daily_new_limit))
        ).mappings().all()
    due = [dict(row) | {'task_type': 'review'} for row in due_rows]
    new = [dict(row) | {'task_type': 'new'} for row in new_rows]
    return due + new


def submit_review(user_id: int, word_id: int, result: str, question_type: str = 'english_to_chinese') -> None:
    init_database()
    now = datetime.now()
    with get_connection() as conn:
        row = conn.execute(
            select(learning_status).where(
                learning_status.c.user_id == int(user_id),
                learning_status.c.word_id == int(word_id),
            )
        ).mappings().first()
        if row is None:
            raise ValueError('找不到该学习者的单词状态。')
        old_level = int(row['mastery_level'])
        decision = calculate_review(old_level, result, now)
        first_learned_at = row['first_learned_at'] or now
        correct_delta = 1 if result in {'正确', '熟练'} else 0
        wrong_delta = 1 if result == '忘记' else 0
        fuzzy_delta = 1 if result == '模糊' else 0
        consecutive_correct = int(row['consecutive_correct']) + 1 if decision.consecutive_correct_change == 'increase' else 0
        updated_wrong_count = int(row['wrong_count']) + wrong_delta
        updated_fuzzy_count = int(row['fuzzy_count']) + fuzzy_delta
        difficult_flag = int(row['difficult_flag'])
        if updated_wrong_count >= 3 or updated_fuzzy_count >= 3:
            difficult_flag = 1
        conn.execute(
            update(learning_status)
            .where(learning_status.c.id == row['id'])
            .values(
                status=decision.status,
                mastery_level=decision.new_level,
                first_learned_at=first_learned_at,
                last_review_at=now,
                next_review_at=decision.next_review_at,
                total_reviews=int(row['total_reviews']) + 1,
                correct_count=int(row['correct_count']) + correct_delta,
                wrong_count=updated_wrong_count,
                fuzzy_count=updated_fuzzy_count,
                consecutive_correct=consecutive_correct,
                difficult_flag=difficult_flag,
            )
        )
        conn.execute(
            insert(review_logs).values(
                user_id=int(user_id), word_id=int(word_id), reviewed_at=now, result=result,
                question_type=question_type, old_level=old_level,
                new_level=decision.new_level, next_review_at=decision.next_review_at,
            )
        )
