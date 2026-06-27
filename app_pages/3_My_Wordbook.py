from __future__ import annotations

import math

import pandas as pd
import streamlit as st
from sqlalchemy import and_, func, or_, select

from modules.auth_ui import require_login
from modules.database import get_connection, init_database, ensure_user_word_status, learning_status, words

init_database()
user_id, display_name = require_login()
ensure_user_word_status(user_id)

st.title("📚 我的词库")
st.caption("v1.3.1 性能优化：分页显示，不再一次加载全部词库。")

with get_connection() as conn:
    chapter_rows = conn.execute(select(words.c.chapter).distinct().order_by(words.c.chapter)).all()

chapters = [row[0] for row in chapter_rows]
selected_chapter = st.selectbox("筛选章节", options=["全部"] + chapters)

status_label_to_value = {
    "全部": "all",
    "未学习": "new",
    "学习中": "learning",
    "复习中": "reviewing",
    "稳定掌握": "mastered",
}
selected_status_label = st.selectbox("筛选状态", options=list(status_label_to_value.keys()))
selected_status = status_label_to_value[selected_status_label]
search_word = st.text_input("搜索单词或释义").strip()

col_a, col_b = st.columns(2)
with col_a:
    page_size = st.selectbox("每页显示", options=[50, 100, 200, 500], index=1)
with col_b:
    st.caption("只加载当前页，几千词也不会明显卡。")

base_join = words.join(learning_status, learning_status.c.word_id == words.c.id)
conditions = [learning_status.c.user_id == int(user_id)]

if selected_chapter != "全部":
    conditions.append(words.c.chapter == selected_chapter)

if selected_status != "all":
    conditions.append(learning_status.c.status == selected_status)

if search_word:
    pattern = f"%{search_word}%"
    conditions.append(or_(words.c.word.ilike(pattern), words.c.annotation.ilike(pattern)))

where_clause = and_(*conditions)

with get_connection() as conn:
    total_count = conn.execute(
        select(func.count()).select_from(base_join).where(where_clause)
    ).scalar_one()

total_count = int(total_count or 0)
total_pages = max(1, math.ceil(total_count / int(page_size)))

page_number = st.number_input("页码", min_value=1, max_value=total_pages, value=1, step=1)
offset = (int(page_number) - 1) * int(page_size)

with get_connection() as conn:
    rows = conn.execute(
        select(
            words.c.book_name,
            words.c.chapter,
            words.c.original_number,
            words.c.word,
            words.c.part_of_speech,
            words.c.annotation,
            words.c.uk_phonetic,
            words.c.us_phonetic,
            learning_status.c.status,
            learning_status.c.mastery_level,
            learning_status.c.total_reviews,
            learning_status.c.next_review_at,
            learning_status.c.difficult_flag,
        )
        .select_from(base_join)
        .where(where_clause)
        .order_by(words.c.chapter, words.c.original_number, words.c.id)
        .limit(int(page_size))
        .offset(int(offset))
    ).mappings().all()

items = []
for r in rows:
    items.append(
        {
            "词汇书": r["book_name"],
            "章节": r["chapter"],
            "编号": r["original_number"],
            "单词": r["word"],
            "词性": r["part_of_speech"],
            "释义": r["annotation"],
            "英式音标": r["uk_phonetic"],
            "美式音标": r["us_phonetic"],
            "状态": {"new": "未学习", "learning": "学习中", "reviewing": "复习中", "mastered": "稳定掌握"}.get(r["status"], r["status"]),
            "记忆等级": r["mastery_level"],
            "复习次数": r["total_reviews"],
            "下次复习": r["next_review_at"],
            "薄弱词": "是" if r["difficult_flag"] else "否",
        }
    )

df = pd.DataFrame(items)

if df.empty:
    st.warning("当前筛选条件下没有词汇。")
else:
    st.metric("当前筛选词数", total_count)
    st.caption(f"第 {page_number} / {total_pages} 页；当前加载 {len(df)} 条。")
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button(
        "导出当前页 CSV",
        data=df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{display_name}_vocabulary_page_{page_number}.csv",
        mime="text/csv",
    )
