from __future__ import annotations

from pathlib import Path

import streamlit as st

from modules.database import get_dashboard_metrics, get_database_mode

APP_VERSION = "v1.4"


def read_version() -> str:
    version_file = Path(__file__).resolve().parents[1] / "VERSION.txt"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return APP_VERSION


def apply_global_style() -> None:
    """轻量美化，不引入额外依赖。"""
    
st.markdown(
        """
        <style>
        :root {
            --ielts-font: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter",
                          "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC",
                          "Helvetica Neue", Arial, sans-serif;
            --ielts-text: #1f2937;
            --ielts-muted: #667085;
            --ielts-border: #e7edf5;
            --ielts-soft-bg: #f8fbff;
            --ielts-card-bg: #ffffff;
            --ielts-primary: #2f6fed;
        }

        html, body, [class*="css"], .stApp, button, input, textarea, select {
            font-family: var(--ielts-font) !important;
            color: var(--ielts-text);
        }

        .block-container {
            padding-top: 2.0rem;
            padding-bottom: 4rem;
            max-width: 1180px;
        }

        h1 {
            letter-spacing: -0.035em;
            font-weight: 750 !important;
            line-height: 1.16 !important;
            margin-bottom: 0.35rem !important;
        }

        h2, h3 {
            letter-spacing: -0.02em;
            font-weight: 700 !important;
        }

        p, li, label, div[data-testid="stMarkdownContainer"] {
            line-height: 1.68;
        }

        div[data-testid="stMetric"] {
            background: var(--ielts-card-bg);
            border: 1px solid var(--ielts-border);
            padding: 14px 16px;
            border-radius: 16px;
            box-shadow: 0 1px 2px rgba(16,24,40,0.04);
        }

        div[data-testid="stMetric"] label {
            color: var(--ielts-muted) !important;
            font-size: 0.86rem !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.58rem !important;
            font-weight: 720 !important;
            letter-spacing: -0.02em;
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid var(--ielts-border);
            background: #f7f9fc;
        }

        section[data-testid="stSidebar"] * {
            font-size: 0.95rem;
        }

        div[role="radiogroup"] label {
            padding: 4px 0;
        }

        .stButton > button {
            border-radius: 12px !important;
            font-weight: 650 !important;
            border: 1px solid #d9e2ef !important;
            min-height: 40px;
        }

        .stButton > button[kind="primary"] {
            background: var(--ielts-primary) !important;
            border-color: var(--ielts-primary) !important;
        }

        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
            border-radius: 12px !important;
        }

        .stDataFrame {
            border-radius: 14px;
            overflow: hidden;
        }

        .ielts-status-card {
            padding: 14px 16px;
            border: 1px solid #e8eef8;
            background: var(--ielts-soft-bg);
            border-radius: 14px;
            margin: 8px 0 14px 0;
            line-height: 1.65;
            font-size: 0.94rem;
        }

        .ielts-ok {
            color: #0f7b4f;
            font-weight: 650;
        }

        .ielts-warn {
            color: #a15c00;
            font-weight: 650;
        }

        .ielts-muted {
            color: var(--ielts-muted);
            font-size: 0.92rem;
        }

        .ielts-step {
            padding: 12px 14px;
            border: 1px solid var(--ielts-border);
            border-radius: 14px;
            background: var(--ielts-card-bg);
            margin-bottom: 10px;
            line-height: 1.7;
        }

        .word-card {
            padding: 30px 28px;
            border: 1px solid var(--ielts-border);
            border-radius: 20px;
            background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
            box-shadow: 0 2px 10px rgba(16,24,40,0.04);
            text-align: center;
            margin: 12px 0 18px 0;
        }

        .word-card .word {
            font-size: 46px;
            font-weight: 780;
            letter-spacing: -0.025em;
            line-height: 1.1;
        }

        .word-card .pos {
            color: var(--ielts-muted);
            font-size: 17px;
            margin-top: 10px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )



def render_top_status(user_id: int | None, display_name: str | None) -> None:
    mode = get_database_mode()
    version = read_version()

    if mode == "cloud-postgres":
        db_text = "云端数据库已连接"
        db_class = "ielts-ok"
    else:
        db_text = "本地数据库模式"
        db_class = "ielts-warn"

    user_text = display_name if user_id else "未登录"
    user_class = "ielts-ok" if user_id else "ielts-warn"

    st.markdown(
        f"""
        <div class="ielts-status-card">
            <span class="{db_class}">● {db_text}</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            <span class="{user_class}">当前学习者：{user_text}</span>
            &nbsp;&nbsp;|&nbsp;&nbsp;
            <span class="ielts-muted">版本：{version}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_status(user_id: int | None, display_name: str | None) -> None:
    st.sidebar.markdown("---")
    st.sidebar.subheader("状态")

    if user_id:
        st.sidebar.success(f"学习者：{display_name}")
    else:
        st.sidebar.warning("尚未登录")

    mode = get_database_mode()
    if mode == "cloud-postgres":
        st.sidebar.caption("数据库：Supabase 云端")
    else:
        st.sidebar.caption("数据库：本地 SQLite")

    st.sidebar.caption(f"版本：{read_version()}")

    if st.sidebar.button("刷新状态", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    if user_id:
        if st.sidebar.button("退出登录", use_container_width=True):
            st.session_state.pop("user_id", None)
            st.session_state.pop("display_name", None)
            st.rerun()


def render_dashboard_cards(user_id: int | None) -> None:
    metrics = get_dashboard_metrics(int(user_id)) if user_id else get_dashboard_metrics(None)

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("公共词库", metrics["total_words"])
    col2.metric("今日到期", metrics["due_reviews"])
    col3.metric("待学新词", metrics["new_words"])
    col4.metric("我的已学", metrics["learned_words"])
    col5.metric("学习者", metrics["total_users"])


def render_next_steps(user_id: int | None) -> None:
    st.subheader("下一步建议")

    if not user_id:
        st.markdown(
            """
            <div class="ielts-step">① 先创建或登录学习者：输入名称和4位以上 PIN。</div>
            <div class="ielts-step">② 登录后进入“批量导入词库”，上传全量或章节 Excel。</div>
            <div class="ielts-step">③ 导入后进入“今日学习”，系统会自动生成你的个人进度。</div>
            """,
            unsafe_allow_html=True,
        )
        return

    metrics = get_dashboard_metrics(int(user_id))
    if metrics["total_words"] == 0:
        st.info("现在还没有公共词库。请进入“批量导入词库”上传 Excel。")
    elif metrics["new_words"] > 0:
        st.success("词库已经准备好。建议进入“今日学习”开始第一组单词。")
    elif metrics["due_reviews"] > 0:
        st.warning("今天有到期复习。建议先完成复习，再学新词。")
    else:
        st.success("今天暂时没有到期任务。可以去“词汇补全中心”补例句，或去“故事记忆”生成故事。")


def render_page_header(title: str, caption: str | None = None) -> None:
    st.title(title)
    if caption:
        st.caption(caption)


def render_operation_hint(text: str, level: str = "info") -> None:
    if level == "success":
        st.success(text)
    elif level == "warning":
        st.warning(text)
    elif level == "error":
        st.error(text)
    else:
        st.info(text)
