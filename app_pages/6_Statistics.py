from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import case, func, select

from modules.auth_ui import require_login
from modules.database import get_connection, init_database, learning_status, review_logs, words

init_database()
user_id, display_name = require_login()

st.title("📊 学习统计")
st.caption("v1.3.1 性能优化：统计由数据库聚合，不再一次读取全部日志。")

with get_connection() as conn:
    summary = conn.execute(
        select(
            func.count(review_logs.c.id).label("total_reviews"),
            func.sum(case((review_logs.c.result.in_(["正确", "熟练"]), 1), else_=0)).label("correct_reviews"),
            func.sum(case((review_logs.c.result == "忘记", 1), else_=0)).label("forgotten_reviews"),
            func.sum(case((review_logs.c.result == "模糊", 1), else_=0)).label("fuzzy_reviews"),
        ).where(review_logs.c.user_id == int(user_id))
    ).mappings().first()

total_reviews = int((summary or {}).get("total_reviews") or 0)
correct_reviews = int((summary or {}).get("correct_reviews") or 0)
forgotten_reviews = int((summary or {}).get("forgotten_reviews") or 0)
fuzzy_reviews = int((summary or {}).get("fuzzy_reviews") or 0)
accuracy = round(correct_reviews / total_reviews * 100, 1) if total_reviews else 0.0

col1, col2, col3, col4 = st.columns(4)
col1.metric("累计复习次数", total_reviews)
col2.metric("正确或熟练", correct_reviews)
col3.metric("完全忘记", forgotten_reviews)
col4.metric("当前正确率", f"{accuracy}%")

if total_reviews == 0:
    st.info("还没有学习记录。请先进入“今日学习”。")
else:
    with get_connection() as conn:
        daily_rows = conn.execute(
            select(
                func.date(review_logs.c.reviewed_at).label("日期"),
                func.count(review_logs.c.id).label("复习次数"),
                func.sum(case((review_logs.c.result.in_(["正确", "熟练"]), 1), else_=0)).label("正确次数"),
            )
            .where(review_logs.c.user_id == int(user_id))
            .group_by(func.date(review_logs.c.reviewed_at))
            .order_by(func.date(review_logs.c.reviewed_at))
        ).mappings().all()

    daily = pd.DataFrame([dict(r) for r in daily_rows])
    if not daily.empty:
        daily["正确率"] = (daily["正确次数"] / daily["复习次数"] * 100).round(1)
        st.subheader("每日学习量")
        st.line_chart(daily.set_index("日期")[["复习次数"]], x_label="日期", y_label="次数")
        st.dataframe(daily.tail(60), use_container_width=True, hide_index=True)

st.subheader("薄弱词")

with get_connection() as conn:
    weak_rows = conn.execute(
        select(
            words.c.word,
            words.c.annotation,
            words.c.chapter,
            learning_status.c.wrong_count,
            learning_status.c.fuzzy_count,
            learning_status.c.total_reviews,
            learning_status.c.mastery_level,
        )
        .select_from(learning_status.join(words, learning_status.c.word_id == words.c.id))
        .where(learning_status.c.user_id == int(user_id), learning_status.c.difficult_flag == 1)
        .order_by(learning_status.c.wrong_count.desc(), learning_status.c.fuzzy_count.desc())
        .limit(100)
    ).mappings().all()

weak_df = pd.DataFrame(
    [
        {
            "单词": r["word"],
            "释义": r["annotation"],
            "章节": r["chapter"],
            "忘记次数": r["wrong_count"],
            "模糊次数": r["fuzzy_count"],
            "总复习次数": r["total_reviews"],
            "当前等级": r["mastery_level"],
        }
        for r in weak_rows
    ]
)

if weak_df.empty:
    st.caption("暂时还没有被系统判定为薄弱词的单词。")
else:
    st.dataframe(weak_df, use_container_width=True, hide_index=True)
