from __future__ import annotations

from pathlib import Path
import runpy
import sys

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from modules.auth_ui import render_login_box
from modules.database import init_database
from modules.ui_status import (
    apply_global_style,
    render_dashboard_cards,
    render_next_steps,
    render_sidebar_status,
    render_top_status,
)

st.set_page_config(
    page_title="IELTS Vocabulary Planner",
    page_icon="📘",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_style()
init_database()

PAGE_MAP = {
    "🏠 首页 / 登录": None,
    "📥 上传词库": "1_Upload_Wordlist.py",
    "📂 批量导入词库": "2_Bulk_Import.py",
    "📚 我的词库": "3_My_Wordbook.py",
    "🧠 今日学习": "4_Today_Study.py",
    "🗓️ 复习计划": "5_Review_Plan.py",
    "📊 学习统计": "6_Statistics.py",
    "⚙️ 词汇补全中心": "7_Enrichment.py",
    "📖 故事记忆": "8_Story_Memory.py",
}

st.sidebar.title("📘 IELTS Planner")
selected_page = st.sidebar.radio("功能导航", list(PAGE_MAP.keys()), index=0)

user_id = st.session_state.get("user_id")
display_name = st.session_state.get("display_name")

render_sidebar_status(user_id, display_name)

page_file = PAGE_MAP[selected_page]

if page_file is not None:
    st.markdown(f"### {selected_page}")
    render_top_status(user_id, display_name)

    page_path = ROOT / "app_pages" / page_file
    if not page_path.exists():
        st.error(f"页面文件不存在：{page_path}")
        st.stop()

    try:
        runpy.run_path(str(page_path), run_name="__main__")
    except Exception as exc:
        st.error("当前页面运行时出现错误。")
        st.exception(exc)
        st.info("如果是刚更新代码后出现的问题，请先 Reboot app；如果仍然存在，把这个错误截图发给开发者。")
    st.stop()

# Home page
st.title("📘 IELTS Vocabulary Planner")
st.caption("v1.3.3 页面状态优化版：更清楚的登录状态、数据库状态、操作引导和刷新按钮。")
render_top_status(user_id, display_name)

if not user_id:
    st.info("请先登录或创建学习者。第一次使用只需要输入一个名称和4位以上 PIN。")
    render_login_box(location="main")
else:
    st.success(f"已经登录：{display_name}")

st.divider()
render_dashboard_cards(user_id)

st.divider()
render_next_steps(user_id)

with st.expander("使用说明", expanded=False):
    st.markdown(
        """
        **推荐流程：**

        1. 首页创建或登录学习者；
        2. 批量导入词库；
        3. 进入今日学习开始背词；
        4. 进入词汇补全中心补音标、例句和翻译；
        5. 学完一组后进入故事记忆生成复习故事。

        **性能建议：**

        - 词汇补全每批先处理 10 个；
        - 自动翻译先关闭，等英文例句补完后再小批量翻译；
        - 大词库查看请使用“我的词库”的分页功能。
        """
    )
