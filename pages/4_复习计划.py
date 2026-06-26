from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from modules.database import get_connection, init_database

st.set_page_config(page_title="复习计划", page_icon="🗓️", layout="wide")
init_database()

st.title("🗓️ 复习计划")

days = st.slider(
    "查看未来多少天",
    min_value=7,
    max_value=60,
    value=14,
    step=1,
)

end_date = date.today() + timedelta(days=int(days))

with get_connection() as connection:
    rows = connection.execute(
        """
        SELECT
            DATE(ls.next_review_at) AS 复习日期,
            COUNT(*) AS 词数
        FROM learning_status ls
        WHERE ls.status != 'new'
          AND ls.next_review_at IS NOT NULL
          AND DATE(ls.next_review_at) <= ?
        GROUP BY DATE(ls.next_review_at)
        ORDER BY DATE(ls.next_review_at)
        """,
        (end_date.isoformat(),),
    ).fetchall()

schedule_df = pd.DataFrame([dict(row) for row in rows])

if schedule_df.empty:
    st.info("当前还没有未来复习任务。先在“今日学习”完成一些新词。")
else:
    st.dataframe(
        schedule_df,
        use_container_width=True,
        hide_index=True,
    )
    st.bar_chart(
        schedule_df.set_index("复习日期")["词数"],
        x_label="复习日期",
        y_label="词数",
    )

st.subheader("近期到期单词")

with get_connection() as connection:
    word_rows = connection.execute(
        """
        SELECT
            w.word AS 单词,
            w.annotation AS 释义,
            w.chapter AS 章节,
            ls.mastery_level AS 等级,
            ls.next_review_at AS 下次复习
        FROM learning_status ls
        JOIN words w ON w.id = ls.word_id
        WHERE ls.status != 'new'
          AND ls.next_review_at IS NOT NULL
          AND DATE(ls.next_review_at) <= ?
        ORDER BY ls.next_review_at
        LIMIT 300
        """,
        (end_date.isoformat(),),
    ).fetchall()

word_df = pd.DataFrame([dict(row) for row in word_rows])

if not word_df.empty:
    st.dataframe(
        word_df,
        use_container_width=True,
        hide_index=True,
    )
