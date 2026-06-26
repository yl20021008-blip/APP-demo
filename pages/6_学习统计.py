from __future__ import annotations
import pandas as pd
import streamlit as st
from sqlalchemy import select
from modules.auth_ui import require_login
from modules.database import get_connection, init_database, learning_status, review_logs, words

st.set_page_config(page_title='学习统计', page_icon='📊', layout='wide')
init_database(); user_id, display_name = require_login()
st.title('📊 学习统计')
with get_connection() as conn:
    logs = conn.execute(select(review_logs).where(review_logs.c.user_id == int(user_id))).mappings().all()
log_rows = [dict(r) for r in logs]
total_reviews = len(log_rows)
correct_reviews = sum(1 for r in log_rows if r['result'] in {'正确', '熟练'})
forgotten_reviews = sum(1 for r in log_rows if r['result'] == '忘记')
fuzzy_reviews = sum(1 for r in log_rows if r['result'] == '模糊')
accuracy = round(correct_reviews / total_reviews * 100, 1) if total_reviews else 0.0
col1, col2, col3, col4 = st.columns(4); col1.metric('累计复习次数', total_reviews); col2.metric('正确或熟练', correct_reviews); col3.metric('完全忘记', forgotten_reviews); col4.metric('当前正确率', f'{accuracy}%')
if not log_rows:
    st.info('还没有学习记录。请先进入“今日学习”。')
else:
    df = pd.DataFrame(log_rows)
    df['日期'] = pd.to_datetime(df['reviewed_at']).dt.date.astype(str)
    daily = df.groupby('日期').agg(复习次数=('id','count'), 正确次数=('result', lambda s: s.isin(['正确','熟练']).sum())).reset_index()
    daily['正确率'] = (daily['正确次数'] / daily['复习次数'] * 100).round(1)
    st.subheader('每日学习量'); st.line_chart(daily.set_index('日期')[['复习次数']], x_label='日期', y_label='次数'); st.dataframe(daily, use_container_width=True, hide_index=True)
st.subheader('薄弱词')
with get_connection() as conn:
    weak_rows = conn.execute(select(words.c.word, words.c.annotation, words.c.chapter, learning_status.c.wrong_count, learning_status.c.fuzzy_count, learning_status.c.total_reviews, learning_status.c.mastery_level).select_from(learning_status.join(words, learning_status.c.word_id == words.c.id)).where(learning_status.c.user_id == int(user_id), learning_status.c.difficult_flag == 1).order_by(learning_status.c.wrong_count.desc(), learning_status.c.fuzzy_count.desc()).limit(100)).mappings().all()
weak_df = pd.DataFrame([{'单词': r['word'], '释义': r['annotation'], '章节': r['chapter'], '忘记次数': r['wrong_count'], '模糊次数': r['fuzzy_count'], '总复习次数': r['total_reviews'], '当前等级': r['mastery_level']} for r in weak_rows])
if weak_df.empty: st.caption('暂时还没有被系统判定为薄弱词的单词。')
else: st.dataframe(weak_df, use_container_width=True, hide_index=True)
