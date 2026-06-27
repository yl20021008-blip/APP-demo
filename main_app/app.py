from __future__ import annotations

from pathlib import Path
import runpy
import sys

import streamlit as st

# Ensure imports work when Streamlit main file path is main_app/app.py
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.auth_ui import render_login_box
from modules.database import get_dashboard_metrics, get_database_mode, init_database
from modules.settings_service import get_setting

st.set_page_config(page_title="IELTS Vocabulary Planner", page_icon="📘", layout="wide")

init_database()

PAGE_MAP = {
    "首页 / 登录": None,
    "上传词库": "1_Upload_Wordlist.py",
    "批量导入词库": "2_Bulk_Import.py",
    "我的词库": "3_My_Wordbook.py",
    "今日学习": "4_Today_Study.py",
    "复习计划": "5_Review_Plan.py",
    "学习统计": "6_Statistics.py",
    "词汇补全中心": "7_Enrichment.py",
    "故事记忆": "8_Story_Memory.py",
}

st.sidebar.title("📘 IELTS Planner")
selected_page = st.sidebar.radio("功能导航", list(PAGE_MAP.keys()), index=0)

user_id = st.session_state.get("user_id")
display_name = st.session_state.get("display_name")

if user_id:
    st.sidebar.success(f"当前学习者：{display_name}")
    if st.sidebar.button("退出登录"):
        st.session_state.pop("user_id", None)
        st.session_state.pop("display_name", None)
        st.rerun()
else:
    st.sidebar.info("请先在首页登录或创建学习者。")

page_file = PAGE_MAP[selected_page]

if page_file is not None:
    page_path = ROOT / "app_pages" / page_file
    if not page_path.exists():
        st.error(f"页面文件不存在：{page_path}")
        st.stop()
    runpy.run_path(str(page_path), run_name="__main__")
    st.stop()

# Home page
st.title("📘 IELTS Vocabulary Planner")
st.caption("v1.3.1 性能优化版：云端保存、用户区分、分页词库、数据库连接池优化。")

if not user_id:
    st.info("请先登录或创建学习者。第一次使用只需要输入一个名称和4位以上 PIN。")
    render_login_box(location="main")
else:
    st.success(f"当前学习者：{display_name}")

metrics = get_dashboard_metrics(int(user_id)) if user_id else get_dashboard_metrics(None)
daily_new_limit = int(get_setting("daily_new_limit", "20"))

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("公共词库总量", metrics["total_words"])
col2.metric("今日到期复习", metrics["due_reviews"])
col3.metric("我的待学新词", metrics["new_words"])
col4.metric("我的已学词", metrics["learned_words"])
col5.metric("学习者数量", metrics["total_users"])

st.caption(f"数据库模式：{get_database_mode()}")
st.divider()

st.subheader("使用顺序")
st.markdown(
    '''
1. 先在首页创建/登录学习者；
2. 进入 **上传词库** 或 **批量导入词库**，导入公共词库；
3. 进入 **词汇补全中心**，补全缺失音标、发音、例句和翻译；
4. 进入 **今日学习**，每个人的学习进度会独立保存；
5. 背完约30个词后，进入 **故事记忆** 生成自己的记忆故事。
'''
)

st.info("性能优化已启用：数据库连接池、初始化缓存、词库分页、SQL聚合统计、小批量补全。")
