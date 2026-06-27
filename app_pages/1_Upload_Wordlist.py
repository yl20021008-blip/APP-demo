from __future__ import annotations

import streamlit as st

from modules.auth_ui import require_login
from modules.admin_service import require_admin_for_public_write
from modules.database import init_database
from modules.importer import import_words, read_uploaded_file

init_database()
user_id, display_name = require_login()

can_write_public = require_admin_for_public_write("上传公共词库")
if not can_write_public:
    st.info("公共词库由管理员统一维护。你可以去“我的词库”和“今日学习”使用已预设的词库。")
    st.stop()


st.title("📥 上传词库")
st.info("状态：上传后会写入公共词库；当前学习者会自动同步学习进度。")
st.caption("v1.3.1 性能优化：预览只显示前200行，避免大文件预览卡顿。")

book_name = st.text_input("词汇书名称", value="雅思词汇真经")
chapter = st.text_input("默认章节名称", value="Chapter 1")
update_existing = st.checkbox("重复词自动补齐旧记录缺失字段", value=True)

uploaded_file = st.file_uploader("选择 Excel / CSV 文件", type=["xlsx", "xls", "csv"])
if uploaded_file is None:
    st.info("请上传包含 Words/word/单词 和 Annotation/meaning/释义 的文件。")
    st.stop()

try:
    preview_df = read_uploaded_file(uploaded_file)
except Exception as exc:
    st.error(f"读取失败：{exc}")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("有效词条", len(preview_df))
col2.metric("表内章节数", preview_df["chapter"].dropna().nunique() or 1)
col3.metric(
    "已有音标数",
    int(
        (
            preview_df["uk_phonetic"].fillna("").astype(str).str.strip().ne("")
            | preview_df["us_phonetic"].fillna("").astype(str).str.strip().ne("")
        ).sum()
    ),
)
col4.metric("缺少例句", int(preview_df["example_sentence"].fillna("").astype(str).str.strip().eq("").sum()))

st.caption("预览前200行：")
st.dataframe(preview_df.head(200), use_container_width=True, hide_index=True)

if st.button("确认导入公共词库", type="primary"):
    progress = st.progress(0)
    status_text = st.empty()

    def on_progress(index: int, total: int, word: str) -> None:
        progress.progress(index / total if total else 1.0)
        status_text.write(f"正在导入 {index}/{total}：{word}")

    try:
        result = import_words(
            preview_df,
            chapter=chapter,
            book_name=book_name,
            update_existing=update_existing,
            user_id=user_id,
            progress_callback=on_progress,
        )
    except Exception as exc:
        st.error(f"导入失败：{exc}")
    else:
        progress.progress(1.0)
        status_text.write("导入完成。")
        st.success(f"导入完成：新增 {result['inserted']} 个，补齐旧记录 {result['updated']} 个，重复 {result['duplicated']} 个。")
