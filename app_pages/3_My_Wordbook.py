from __future__ import annotations
import pandas as pd
import streamlit as st
from sqlalchemy import select
from modules.auth_ui import require_login
from modules.database import get_connection, init_database, ensure_user_word_status, learning_status, words
init_database()
user_id, display_name = require_login()
ensure_user_word_status(user_id)
st.title('📚 我的词库')
st.caption('词库是公共的，状态和进度是你的个人记录。')
with get_connection() as conn:
    chapter_rows = conn.execute(select(words.c.chapter).distinct().order_by(words.c.chapter)).all()
chapters = [row[0] for row in chapter_rows]
selected_chapter = st.selectbox('筛选章节', options=['全部'] + chapters)
status_label_to_value = {'全部': 'all', '未学习': 'new', '学习中': 'learning', '复习中': 'reviewing', '稳定掌握': 'mastered'}
selected_status_label = st.selectbox('筛选状态', options=list(status_label_to_value.keys()))
selected_status = status_label_to_value[selected_status_label]
search_word = st.text_input('搜索单词或释义').strip().lower()
with get_connection() as conn:
    rows = conn.execute(
        select(words, learning_status.c.status, learning_status.c.mastery_level, learning_status.c.total_reviews, learning_status.c.next_review_at, learning_status.c.difficult_flag)
        .select_from(words.join(learning_status, learning_status.c.word_id == words.c.id))
        .where(learning_status.c.user_id == int(user_id))
        .order_by(words.c.chapter, words.c.original_number, words.c.id)
    ).mappings().all()
items = []
for row in rows:
    r = dict(row)
    if selected_chapter != '全部' and r['chapter'] != selected_chapter:
        continue
    if selected_status != 'all' and r['status'] != selected_status:
        continue
    if search_word and search_word not in str(r['word']).lower() and search_word not in str(r.get('annotation') or '').lower():
        continue
    items.append({'词汇书': r['book_name'], '章节': r['chapter'], '编号': r['original_number'], '单词': r['word'], '词性': r['part_of_speech'], '释义': r['annotation'], '英式音标': r['uk_phonetic'], '美式音标': r['us_phonetic'], '状态': {'new':'未学习','learning':'学习中','reviewing':'复习中','mastered':'稳定掌握'}.get(r['status'], r['status']), '记忆等级': r['mastery_level'], '复习次数': r['total_reviews'], '下次复习': r['next_review_at'], '薄弱词': '是' if r['difficult_flag'] else '否'})
df = pd.DataFrame(items)
if df.empty:
    st.warning('当前筛选条件下没有词汇。')
else:
    st.metric('当前显示词数', len(df))
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button('导出当前词库为 CSV', data=df.to_csv(index=False).encode('utf-8-sig'), file_name=f'{display_name}_vocabulary_export.csv', mime='text/csv')
