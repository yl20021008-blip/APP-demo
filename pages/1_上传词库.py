from __future__ import annotations

import streamlit as st

from modules.database import init_database
from modules.importer import import_words, read_uploaded_excel

st.set_page_config(page_title="上传词库", page_icon="📥", layout="wide")
init_database()

st.title("📥 上传词库")
st.caption("建议一次上传一个完整章节，而不是每天上传少量单词。")

book_name = st.text_input("词汇书名称", value="雅思词汇真经")
chapter = st.text_input("章节名称", value="Chapter 13")

uploaded_file = st.file_uploader(
    "选择 Excel 文件",
    type=["xlsx", "xls"],
)

if uploaded_file is None:
    st.info("请上传包含 Words、Annotation 等字段的 Excel 文件。")
    st.stop()

try:
    preview_df = read_uploaded_excel(uploaded_file)
except Exception as exc:
    st.error(f"读取失败：{exc}")
    st.stop()

col1, col2, col3 = st.columns(3)
col1.metric("有效词条", len(preview_df))
col2.metric(
    "自报熟悉",
    int(preview_df["self_reported_known"].sum()),
)
col3.metric(
    "缺少例句",
    int(
        preview_df["example_sentence"]
        .fillna("")
        .astype(str)
        .str.strip()
        .eq("")
        .sum()
    ),
)

st.dataframe(
    preview_df,
    use_container_width=True,
    hide_index=True,
)

if st.button("确认导入数据库", type="primary"):
    try:
        inserted, duplicated = import_words(
            preview_df,
            chapter=chapter,
            book_name=book_name,
        )
    except Exception as exc:
        st.error(f"导入失败：{exc}")
    else:
        st.success(
            f"导入完成：新增 {inserted} 个词，跳过重复 {duplicated} 个词。"
        )
