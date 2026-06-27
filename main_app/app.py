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
    render_bottom_nav,
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

COMMON_PAGES = {
    "home": ("🏠 首页", None),
    "today": ("🧠 今日学习", "4_Today_Study.py"),
    "review": ("🗓️ 复习计划", "5_Review_Plan.py"),
    "story": ("📖 故事记忆", "8_Story_Memory.py"),
    "stats": ("📊 学习统计", "6_Statistics.py"),
}

SIDE_PAGES = {
    "wordbook": ("📚 我的词库", "3_My_Wordbook.py"),
    "upload": ("📥 上传词库", "1_Upload_Wordlist.py"),
    "bulk": ("📂 批量导入词库", "2_Bulk_Import.py"),
    "enrichment": ("⚙️ 词汇补全中心", "7_Enrichment.py"),
    "admin": ("🛡️ 公共词库管理", "9_Admin_Public_Wordbook.py"),
}

ALL_PAGES = {**COMMON_PAGES, **SIDE_PAGES}

# Query param routing
try:
    current_page = st.query_params.get("page", "home")
except Exception:
    current_page = "home"

if current_page not in ALL_PAGES:
    current_page = "home"

user_id = st.session_state.get("user_id")
display_name = st.session_state.get("display_name")

st.sidebar.title("📘 IELTS Planner")
st.sidebar.caption("常用功能已移到底部导航。")

with st.sidebar.expander("📚 词库与管理", expanded=False):
    for slug in ["wordbook", "upload", "bulk", "enrichment", "admin"]:
        label, _ = SIDE_PAGES[slug]
        prefix = "● " if current_page == slug else ""
        if st.button(prefix + label, key=f"side_{slug}", use_container_width=True):
            st.query_params["page"] = slug
            st.rerun()

with st.sidebar.expander("🧭 常用功能", expanded=False):
    for slug, (label, _) in COMMON_PAGES.items():
        prefix = "● " if current_page == slug else ""
        if st.button(prefix + label, key=f"common_{slug}", use_container_width=True):
            st.query_params["page"] = slug
            st.rerun()

render_sidebar_status(user_id, display_name)

page_title, page_file = ALL_PAGES[current_page]

if page_file is not None:
    st.markdown(f"### {page_title}")
    render_top_status(user_id, display_name)

    page_path = ROOT / "app_pages" / page_file
    if not page_path.exists():
        st.error(f"页面文件不存在：{page_path}")
        render_bottom_nav(current_page if current_page in COMMON_PAGES else "home")
        st.stop()

    try:
        runpy.run_path(str(page_path), run_name="__main__")
    except Exception as exc:
        st.error("当前页面运行时出现错误。")
        st.exception(exc)
        st.info("如果是刚更新代码后出现的问题，请先 Reboot app；如果仍然存在，把这个错误截图发给开发者。")

    render_bottom_nav(current_page if current_page in COMMON_PAGES else "home")
    st.stop()

# Home page
st.title("📘 IELTS Vocabulary Planner")
st.caption("v1.5 莫兰迪科研风导航版：常用功能在底部切换，词库与管理功能收纳到左侧。")
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
        **新的页面结构：**

        - 底部导航：首页、今日学习、复习计划、故事记忆、学习统计。
        - 左侧栏：我的词库、上传词库、批量导入、词汇补全、公共词库管理。

        **建议使用方式：**

        1. 管理员先从左侧进入“公共词库管理”，预设公共词库；
        2. 普通学习者主要使用底部导航；
        3. 词库维护类操作统一收纳在左侧，减少误操作。
        """
    )

render_bottom_nav("home")
