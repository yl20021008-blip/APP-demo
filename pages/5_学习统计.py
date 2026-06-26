from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.database import get_connection, init_database

st.set_page_config(page_title="学习统计", page_icon="📊", layout="wide")
init_database()

st.title("📊 学习统计")

with get_connection() as connection:
    summary = connection.execute(
        """
        SELECT
            COUNT(*) AS total_reviews,
            SUM(CASE WHEN result IN ('正确', '熟练') THEN 1 ELSE 0 END)
                AS correct_reviews,
            SUM(CASE WHEN result = '忘记' THEN 1 ELSE 0 END)
                AS forgotten_reviews,
            SUM(CASE WHEN result = '模糊' THEN 1 ELSE 0 END)
                AS fuzzy_reviews
        FROM review_logs
        """
    ).fetchone()

total_reviews = int(summary["total_reviews"] or 0)
correct_reviews = int(summary["correct_reviews"] or 0)
forgotten_reviews = int(summary["forgotten_reviews"] or 0)
fuzzy_reviews = int(summary["fuzzy_reviews"] or 0)
accuracy = (
    round(correct_reviews / total_reviews * 100, 1)
    if total_reviews
    else 0.0
)

col1, col2, col3, col4 = st.columns(4)
col1.metric("累计复习次数", total_reviews)
col2.metric("正确或熟练", correct_reviews)
col3.metric("完全忘记", forgotten_reviews)
col4.metric("当前正确率", f"{accuracy}%")

with get_connection() as connection:
    daily_rows = connection.execute(
        """
        SELECT
            DATE(reviewed_at) AS 日期,
            COUNT(*) AS 复习次数,
            SUM(CASE WHEN result IN ('正确', '熟练') THEN 1 ELSE 0 END)
                AS 正确次数
        FROM review_logs
        GROUP BY DATE(reviewed_at)
        ORDER BY DATE(reviewed_at)
        """
    ).fetchall()

daily_df = pd.DataFrame([dict(row) for row in daily_rows])

if daily_df.empty:
    st.info("还没有学习记录。请先进入“今日学习”。")
else:
    daily_df["正确率"] = (
        daily_df["正确次数"] / daily_df["复习次数"] * 100
    ).round(1)

    st.subheader("每日学习量")
    st.line_chart(
        daily_df.set_index("日期")[["复习次数"]],
        x_label="日期",
        y_label="次数",
    )

    st.dataframe(
        daily_df,
        use_container_width=True,
        hide_index=True,
    )

st.subheader("薄弱词")

with get_connection() as connection:
    weak_rows = connection.execute(
        """
        SELECT
            w.word AS 单词,
            w.annotation AS 释义,
            w.chapter AS 章节,
            ls.wrong_count AS 忘记次数,
            ls.fuzzy_count AS 模糊次数,
            ls.total_reviews AS 总复习次数,
            ls.mastery_level AS 当前等级
        FROM learning_status ls
        JOIN words w ON w.id = ls.word_id
        WHERE ls.difficult_flag = 1
        ORDER BY
            ls.wrong_count DESC,
            ls.fuzzy_count DESC,
            ls.total_reviews DESC
        LIMIT 100
        """
    ).fetchall()

weak_df = pd.DataFrame([dict(row) for row in weak_rows])

if weak_df.empty:
    st.caption("暂时还没有被系统判定为薄弱词的单词。")
else:
    st.dataframe(
        weak_df,
        use_container_width=True,
        hide_index=True,
    )
