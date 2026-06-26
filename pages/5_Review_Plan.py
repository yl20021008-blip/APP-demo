from __future__ import annotations
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from sqlalchemy import select
from modules.auth_ui import require_login
from modules.database import get_connection, init_database, ensure_user_word_status, learning_status, words

st.set_page_config(page_title='复习计划', page_icon='🗓️', layout='wide')
init_database(); user_id, display_name = require_login(); ensure_user_word_status(user_id)
st.title('🗓️ 复习计划')
days = st.slider('查看未来多少天', min_value=7, max_value=60, value=14, step=1)
end_dt = date.today() + timedelta(days=int(days))
with get_connection() as conn:
    rows = conn.execute(select(learning_status.c.next_review_at).where(learning_status.c.user_id == int(user_id), learning_status.c.status != 'new', learning_status.c.next_review_at.is_not(None))).all()
counts = {}
for (dt,) in rows:
    if dt and dt.date() <= end_dt:
        counts[dt.date().isoformat()] = counts.get(dt.date().isoformat(), 0) + 1
schedule_df = pd.DataFrame([{'复习日期': k, '词数': v} for k, v in sorted(counts.items())])
if schedule_df.empty:
    st.info('当前还没有未来复习任务。先在“今日学习”完成一些新词。')
else:
    st.dataframe(schedule_df, use_container_width=True, hide_index=True)
    st.bar_chart(schedule_df.set_index('复习日期')['词数'], x_label='复习日期', y_label='词数')
st.subheader('近期到期单词')
with get_connection() as conn:
    word_rows = conn.execute(
        select(words.c.word, words.c.annotation, words.c.chapter, learning_status.c.mastery_level, learning_status.c.next_review_at)
        .select_from(learning_status.join(words, learning_status.c.word_id == words.c.id))
        .where(learning_status.c.user_id == int(user_id), learning_status.c.status != 'new', learning_status.c.next_review_at.is_not(None))
        .order_by(learning_status.c.next_review_at).limit(300)
    ).mappings().all()
items = [{'单词': r['word'], '释义': r['annotation'], '章节': r['chapter'], '等级': r['mastery_level'], '下次复习': r['next_review_at']} for r in word_rows if r['next_review_at'] and r['next_review_at'].date() <= end_dt]
if items: st.dataframe(pd.DataFrame(items), use_container_width=True, hide_index=True)
