from __future__ import annotations

from pathlib import Path

import streamlit as st

from modules.database import get_dashboard_metrics, get_database_mode

APP_VERSION = "v1.5"


def read_version() -> str:
    version_file = Path(__file__).resolve().parents[1] / "VERSION.txt"
    if version_file.exists():
        return version_file.read_text(encoding="utf-8").strip()
    return APP_VERSION


def apply_global_style() -> None:
    """Morandi + research style global UI."""
    st.markdown(
        """
        <style>
        :root {
            --ielts-font: -apple-system, BlinkMacSystemFont, "Segoe UI", "Inter",
                          "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC",
                          "Helvetica Neue", Arial, sans-serif;

            /* Morandi research palette */
            --bg: #F4F2EC;
            --surface: #FBFAF6;
            --surface-2: #F0EEE7;
            --surface-3: #E8E4DA;
            --text: #30363A;
            --muted: #717A7E;
            --border: #DCD7CC;
            --border-2: #CFC8BC;
            --primary: #6F847D;
            --primary-2: #8FA29A;
            --primary-soft: #DDE6E1;
            --accent: #A99786;
            --accent-soft: #E7DED4;
            --blue-gray: #778899;
            --warning: #A8895E;
            --danger: #B17870;
            --success: #6F847D;
        }

        html, body, [class*="css"], .stApp, button, input, textarea, select {
            font-family: var(--ielts-font) !important;
            color: var(--text);
        }

        .stApp {
            background:
              radial-gradient(circle at 12% 10%, rgba(221,230,225,0.60) 0, rgba(221,230,225,0) 28%),
              linear-gradient(180deg, #F7F5EF 0%, var(--bg) 100%);
        }

        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 7.0rem;
            max-width: 1180px;
        }

        h1 {
            letter-spacing: -0.035em;
            font-weight: 760 !important;
            line-height: 1.14 !important;
            margin-bottom: 0.40rem !important;
            color: #2E3437;
        }

        h2, h3 {
            letter-spacing: -0.02em;
            font-weight: 720 !important;
            color: #384044;
        }

        p, li, label, div[data-testid="stMarkdownContainer"] {
            line-height: 1.70;
        }

        .ielts-page-title {
            margin-bottom: 0.2rem;
        }

        div[data-testid="stMetric"] {
            background: rgba(251,250,246,0.92);
            border: 1px solid var(--border);
            padding: 14px 16px;
            border-radius: 18px;
            box-shadow: 0 6px 18px rgba(48,54,58,0.045);
        }

        div[data-testid="stMetric"] label {
            color: var(--muted) !important;
            font-size: 0.84rem !important;
        }

        div[data-testid="stMetricValue"] {
            font-size: 1.48rem !important;
            font-weight: 740 !important;
            letter-spacing: -0.02em;
            color: #2F383A;
        }

        section[data-testid="stSidebar"] {
            border-right: 1px solid var(--border);
            background: rgba(240,238,231,0.96);
        }

        section[data-testid="stSidebar"] * {
            font-size: 0.94rem;
        }

        section[data-testid="stSidebar"] .stButton > button {
            justify-content: flex-start;
            text-align: left;
            background: rgba(251,250,246,0.70);
            border: 1px solid var(--border) !important;
            color: #3E4649;
            min-height: 38px;
        }

        section[data-testid="stSidebar"] .stButton > button:hover {
            background: var(--primary-soft);
            border-color: var(--primary-2) !important;
            color: #253432;
        }

        .stButton > button {
            border-radius: 14px !important;
            font-weight: 650 !important;
            border: 1px solid var(--border) !important;
            min-height: 40px;
            background: var(--surface);
            color: var(--text);
        }

        .stButton > button[kind="primary"] {
            background: var(--primary) !important;
            border-color: var(--primary) !important;
            color: #FFFFFF !important;
        }

        .stButton > button:hover {
            border-color: var(--primary-2) !important;
            box-shadow: 0 4px 14px rgba(111,132,125,0.14);
        }

        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
            border-radius: 14px !important;
            background: rgba(251,250,246,0.96) !important;
            border-color: var(--border) !important;
        }

        .stDataFrame {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid var(--border);
        }

        div[data-testid="stAlert"] {
            border-radius: 16px;
            border: 1px solid rgba(207,200,188,0.86);
        }

        .ielts-status-card {
            padding: 13px 16px;
            border: 1px solid var(--border);
            background: rgba(251,250,246,0.82);
            border-radius: 16px;
            margin: 8px 0 14px 0;
            line-height: 1.65;
            font-size: 0.93rem;
            box-shadow: 0 4px 14px rgba(48,54,58,0.035);
        }

        .ielts-ok {
            color: #526E67;
            font-weight: 700;
        }

        .ielts-warn {
            color: #8B6E45;
            font-weight: 700;
        }

        .ielts-muted {
            color: var(--muted);
            font-size: 0.92rem;
        }

        .ielts-step {
            padding: 12px 14px;
            border: 1px solid var(--border);
            border-radius: 16px;
            background: rgba(251,250,246,0.90);
            margin-bottom: 10px;
            line-height: 1.7;
        }

        .word-card {
            padding: 30px 28px;
            border: 1px solid var(--border);
            border-radius: 22px;
            background: linear-gradient(180deg, rgba(251,250,246,0.98) 0%, rgba(240,238,231,0.86) 100%);
            box-shadow: 0 10px 26px rgba(48,54,58,0.055);
            text-align: center;
            margin: 12px 0 18px 0;
        }

        .word-card .word {
            font-size: 46px;
            font-weight: 780;
            letter-spacing: -0.025em;
            line-height: 1.1;
            color: #2E3437;
        }

        .word-card .pos {
            color: var(--muted);
            font-size: 17px;
            margin-top: 10px;
        }

        /* Fixed bottom nav */
        .bottom-nav-wrap {
            position: fixed;
            left: 50%;
            bottom: 18px;
            transform: translateX(-50%);
            width: min(780px, calc(100vw - 36px));
            background: rgba(251,250,246,0.94);
            border: 1px solid rgba(207,200,188,0.88);
            box-shadow: 0 14px 38px rgba(48,54,58,0.16);
            border-radius: 24px;
            z-index: 999999;
            padding: 8px;
            backdrop-filter: blur(16px);
        }

        .bottom-nav {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 6px;
        }

        .bottom-nav a {
            text-decoration: none !important;
            color: #4C5558 !important;
            padding: 10px 8px;
            border-radius: 18px;
            text-align: center;
            font-size: 13px;
            font-weight: 650;
            line-height: 1.2;
            transition: all 0.18s ease;
            border: 1px solid transparent;
        }

        .bottom-nav a:hover {
            background: var(--primary-soft);
            border-color: var(--primary-2);
            color: #263532 !important;
        }

        .bottom-nav a.active {
            background: var(--primary);
            color: #FFFFFF !important;
            box-shadow: 0 6px 16px rgba(111,132,125,0.25);
        }

        .bottom-nav .nav-icon {
            display: block;
            font-size: 18px;
            margin-bottom: 3px;
        }

        @media (max-width: 760px) {
            .bottom-nav-wrap {
                bottom: 10px;
                width: calc(100vw - 20px);
                border-radius: 20px;
            }
            .bottom-nav a {
                font-size: 11px;
                padding: 8px 4px;
            }
            .bottom-nav .nav-icon {
                font-size: 17px;
            }
            .word-card .word {
                font-size: 36px;
            }
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
            <div class="ielts-step">② 登录后从底部导航进入“今日学习”。</div>
            <div class="ielts-step">③ 管理员在左侧“公共词库管理”统一维护预设词库。</div>
            """,
            unsafe_allow_html=True,
        )
        return

    metrics = get_dashboard_metrics(int(user_id))
    if metrics["total_words"] == 0:
        st.info("现在还没有公共词库。管理员请从左侧进入“公共词库管理”导入预设词库。")
    elif metrics["new_words"] > 0:
        st.success("词库已经准备好。建议从底部导航进入“今日学习”。")
    elif metrics["due_reviews"] > 0:
        st.warning("今天有到期复习。建议先从底部导航进入“复习计划”或“今日学习”。")
    else:
        st.success("今天暂时没有到期任务。可以进入“故事记忆”或查看“学习统计”。")


def render_bottom_nav(active_slug: str) -> None:
    items = [
        ("home", "🏠", "首页"),
        ("today", "🧠", "学习"),
        ("review", "🗓️", "复习"),
        ("story", "📖", "故事"),
        ("stats", "📊", "统计"),
    ]

    links = []
    for slug, icon, label in items:
        active = "active" if slug == active_slug else ""
        links.append(
            f'<a class="{active}" href="?page={slug}"><span class="nav-icon">{icon}</span>{label}</a>'
        )

    st.markdown(
        f"""
        <div class="bottom-nav-wrap">
            <div class="bottom-nav">
                {''.join(links)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_page_header(title: str, caption: str | None = None) -> None:
    st.markdown(f'<div class="ielts-page-title"><h1>{title}</h1></div>', unsafe_allow_html=True)
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
