from __future__ import annotations

import pandas as pd
import streamlit as st
from sqlalchemy import select

from modules.auth_ui import require_login
from modules.database import get_connection, init_database, words
from modules.enrichment_service import enrich_words, get_enrichment_summary

init_database()
user_id, display_name = require_login()

st.title("⚙️ 词汇补全中心")
st.warning("性能提示：补全中心最耗时，建议每批10个，先关闭自动翻译。")
st.caption("v1.3.1 性能优化：默认小批量处理，历史记录只显示最近50条。")

with get_connection() as conn:
    chapter_rows = conn.execute(select(words.c.chapter).distinct().order_by(words.c.chapter)).all()

chapters = [row[0] for row in chapter_rows]
selected_chapter = st.selectbox("选择章节", options=["全部"] + chapters)

summary = get_enrichment_summary(selected_chapter)
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("词数", summary["total"])
col2.metric("缺少音标", summary["missing_phonetic"])
col3.metric("缺少例句", summary["missing_example"])
col4.metric("缺少翻译", summary["missing_translation"])
col5.metric("生成例句", summary.get("generated_examples", 0))
col6.metric("失败记录", summary["failed"])

st.divider()

left, right = st.columns(2)

with left:
    batch_size = st.slider("每批处理数量", min_value=1, max_value=50, value=10, step=5)
    fill_missing_example = st.checkbox("原书无例句时，优先补充词典例句", value=True)
    auto_generate_example = st.checkbox("词典没有例句时，自动生成雅思学习例句", value=True)
    translate_example = st.checkbox("自动翻译英文例句", value=False, help="翻译 API 最慢。建议先关掉，等英文例句补完后再小批量翻译。")

with right:
    generated_style_label = st.selectbox("生成例句风格", options=["雅思学术风格", "日常理解风格"], index=0)
    provider_label = st.selectbox("翻译服务", options=["MyMemory（默认，无需密钥）", "DeepL（需要API密钥）", "本批不翻译"])
    retry_failed = st.checkbox("仅重试之前失败的词", value=False)
    force_overwrite = st.checkbox("强制重新查询并覆盖自动补全字段", value=False)

provider_mapping = {
    "MyMemory（默认，无需密钥）": "mymemory",
    "DeepL（需要API密钥）": "deepl",
    "本批不翻译": "none",
}
style_mapping = {"雅思学术风格": "ielts", "日常理解风格": "daily"}
selected_provider = provider_mapping[provider_label]

st.info("性能建议：先每批10个，并关闭自动翻译；确认稳定后再开翻译小批量处理。")

if st.button("开始自动补全", type="primary", use_container_width=True):
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(index: int, total: int, word: str) -> None:
        progress_bar.progress(index / total if total else 1.0)
        status_text.write(f"正在处理 {index}/{total}：{word}")

    with st.spinner("正在查询词典、补例句并翻译，请不要重复点击……"):
        result = enrich_words(
            chapter=selected_chapter,
            limit=batch_size,
            fill_missing_example=fill_missing_example,
            translate_example=(translate_example and selected_provider != "none"),
            retry_failed=retry_failed,
            force_overwrite=force_overwrite,
            translation_provider=selected_provider,
            auto_generate_example=auto_generate_example,
            generated_example_style=style_mapping[generated_style_label],
            progress_callback=update_progress,
        )

    progress_bar.progress(1.0)
    status_text.write("本批处理完成。")

    r1, r2, r3, r4, r5, r6 = st.columns(6)
    r1.metric("本批处理", result["processed"])
    r2.metric("完整完成", result["completed"])
    r3.metric("部分完成", result["partial"])
    r4.metric("失败", result["failed"])
    r5.metric("词典例句", result.get("dictionary_examples", 0))
    r6.metric("生成例句", result.get("generated_examples", 0))

    if result["items"]:
        st.dataframe(pd.DataFrame(result["items"]).head(50), use_container_width=True, hide_index=True)

st.divider()
st.subheader("最近的补全记录")

with get_connection() as conn:
    rows = conn.execute(
        select(
            words.c.word,
            words.c.chapter,
            words.c.uk_phonetic,
            words.c.us_phonetic,
            words.c.example_sentence,
            words.c.example_translation,
            words.c.example_source,
            words.c.translation_source,
            words.c.enrichment_status,
            words.c.enrichment_error,
            words.c.last_enriched_at,
        )
        .where(words.c.last_enriched_at.is_not(None))
        .order_by(words.c.last_enriched_at.desc())
        .limit(50)
    ).mappings().all()

history_df = pd.DataFrame(
    [
        {
            "单词": r["word"],
            "章节": r["chapter"],
            "英式音标": r["uk_phonetic"],
            "美式音标": r["us_phonetic"],
            "英文例句": r["example_sentence"],
            "中文翻译": r["example_translation"],
            "例句来源": r["example_source"],
            "翻译来源": r["translation_source"],
            "状态": r["enrichment_status"],
            "备注/错误": r["enrichment_error"],
            "最后处理时间": r["last_enriched_at"],
        }
        for r in rows
    ]
)

if history_df.empty:
    st.caption("还没有自动补全记录。")
else:
    st.caption("仅显示最近50条，避免页面加载过慢。")
    st.dataframe(history_df, use_container_width=True, hide_index=True)
