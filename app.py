from __future__ import annotations

import streamlit as st

from modules.database import get_dashboard_metrics, init_database
from modules.settings_service import get_setting

st.set_page_config(
    page_title="IELTS Vocabulary Planner",
    page_icon="📘",
    layout="wide",
)

init_database()

st.title("📘 IELTS Vocabulary Planner")
st.caption("雅思词汇真经：词库导入、音标补全、每日学习、间隔复习与故事记忆。")

metrics = get_dashboard_metrics()
daily_new_limit = int(get_setting("daily_new_limit", "20"))

col1, col2, col3, col4 = st.columns(4)
col1.metric("词库总量", metrics["total_words"])
col2.metric("今日到期复习", metrics["due_reviews"])
col3.metric("待学习新词", metrics["new_words"])
col4.metric("每日新词上限", daily_new_limit)

st.divider()

st.subheader("推荐使用顺序")
st.markdown(
    """
1. 进入 **上传词库**，上传《雅思词汇真经》Excel 章节表；
2. 进入 **词汇补全中心**，补全音标、发音、缺失例句与例句翻译；
3. 进入 **今日学习**，先复习到期词，再学习新词；
4. 背完约30个词后，进入 **故事记忆**，生成一篇中英双语记忆故事；
5. 在 **复习计划** 和 **学习统计** 中检查进度。
"""
)

st.info(
    "当前版本适合本地学习和 Streamlit Demo 展示。"
    "如果要长期在线保存学习记录，下一步建议接入 Supabase / PostgreSQL 云数据库。"
)
