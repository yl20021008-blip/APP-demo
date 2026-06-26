from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.database import get_connection, init_database

st.set_page_config(page_title="我的词库", page_icon="📚", layout="wide")
init_database()

st.title("📚 我的词库")

with get_connection() as connection:
    chapter_rows = connection.execute(
        """
        SELECT DISTINCT chapter
        FROM words
        ORDER BY chapter
        """
    ).fetchall()

chapters = [row["chapter"] for row in chapter_rows]
selected_chapter = st.selectbox(
    "筛选章节",
    options=["全部"] + chapters,
)

status_label_to_value = {
    "全部": "all",
    "未学习": "new",
    "学习中": "learning",
    "复习中": "reviewing",
    "稳定掌握": "mastered",
}
selected_status_label = st.selectbox(
    "筛选状态",
    options=list(status_label_to_value.keys()),
)
selected_status = status_label_to_value[selected_status_label]

search_word = st.text_input("搜索单词或释义").strip()

where_clauses = []
params: list[object] = []

if selected_chapter != "全部":
    where_clauses.append("w.chapter = ?")
    params.append(selected_chapter)

if selected_status != "all":
    where_clauses.append("ls.status = ?")
    params.append(selected_status)

if search_word:
    where_clauses.append(
        "(w.word LIKE ? OR w.annotation LIKE ?)"
    )
    params.extend([f"%{search_word}%", f"%{search_word}%"])

where_sql = ""
if where_clauses:
    where_sql = "WHERE " + " AND ".join(where_clauses)

query = f"""
    SELECT
        w.id,
        w.chapter AS 章节,
        w.original_number AS 编号,
        w.word AS 单词,
        w.part_of_speech AS 词性,
        w.annotation AS 释义,
        w.expansion AS 派生词,
        w.collocation AS 固定搭配,
        w.example_sentence AS 例句,
        CASE ls.status
            WHEN 'new' THEN '未学习'
            WHEN 'learning' THEN '学习中'
            WHEN 'reviewing' THEN '复习中'
            WHEN 'mastered' THEN '稳定掌握'
            ELSE ls.status
        END AS 状态,
        ls.mastery_level AS 记忆等级,
        ls.total_reviews AS 复习次数,
        ls.next_review_at AS 下次复习,
        CASE ls.difficult_flag
            WHEN 1 THEN '是'
            ELSE '否'
        END AS 薄弱词
    FROM words w
    JOIN learning_status ls ON ls.word_id = w.id
    {where_sql}
    ORDER BY
        w.chapter,
        COALESCE(w.original_number, 999999),
        w.id
"""

with get_connection() as connection:
    rows = connection.execute(query, params).fetchall()

df = pd.DataFrame([dict(row) for row in rows])

if df.empty:
    st.warning("当前筛选条件下没有词汇。")
else:
    st.metric("当前显示词数", len(df))
    st.dataframe(
        df.drop(columns=["id"]),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "导出当前词库为 CSV",
        data=df.drop(columns=["id"]).to_csv(index=False).encode("utf-8-sig"),
        file_name="vocabulary_export.csv",
        mime="text/csv",
    )
