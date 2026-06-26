from __future__ import annotations
from modules.database import get_connection, get_database_mode, init_database, users, words, learning_status, review_logs, story_groups
from sqlalchemy import select, func

init_database()
with get_connection() as conn:
    word_count = conn.execute(select(func.count()).select_from(words)).scalar_one()
    user_count = conn.execute(select(func.count()).select_from(users)).scalar_one()
    status_count = conn.execute(select(func.count()).select_from(learning_status)).scalar_one()
    log_count = conn.execute(select(func.count()).select_from(review_logs)).scalar_one()
    story_count = conn.execute(select(func.count()).select_from(story_groups)).scalar_one()
print('=' * 68)
print('IELTS Vocabulary App v1.2 Cloud User 检查')
print('=' * 68)
print(f'数据库模式：{get_database_mode()}')
print(f'words：{word_count}')
print(f'users：{user_count}')
print(f'learning_status：{status_count}')
print(f'review_logs：{log_count}')
print(f'story_groups：{story_count}')
print('检查结果：通过。')
print('=' * 68)
