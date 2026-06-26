from __future__ import annotations

import pandas as pd
import streamlit as st

from modules.database import get_connection, init_database
from modules.enrichment_service import (
    enrich_words,
    get_enrichment_summary,
)

st.set_page_config(
    page_title="词汇补全中心",
    page_icon="⚙️",
    layout="wide",
)
init_database()

st.title("⚙️ 词汇补全中心")
st.caption(
    "自动补全音标、发音、缺失英文例句和例句中文翻译。"
    "默认只填空白字段，不覆盖原书内容。"
)

with get_connection() as connection:
    chapter_rows = connection.execute(
        """
        SELECT DISTINCT chapter
        FROM words
        ORDER BY chapter
        """
    ).fetchall()

chapters = [row["chapter"] for row in chapter_rows]
selected_chapter = st.selectbox(
    "选择章节",
    options=["全部"] + chapters,
)

summary = get_enrichment_summary(selected_chapter)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("词数", summary["total"])
col2.metric("缺少音标", summary["missing_phonetic"])
col3.metric("缺少例句", summary["missing_example"])
col4.metric("缺少翻译", summary["missing_translation"])
col5.metric("失败记录", summary["failed"])

st.divider()

left, right = st.columns(2)

with left:
    batch_size = st.slider(
        "每批处理数量",
        min_value=1,
        max_value=50,
        value=10,
        step=1,
    )
    fill_missing_example = st.checkbox(
        "原书无例句时，补充词典例句",
        value=True,
    )
    translate_example = st.checkbox(
        "自动翻译英文例句",
        value=True,
    )

with right:
    provider_label = st.selectbox(
        "翻译服务",
        options=[
            "MyMemory（默认，无需密钥）",
            "DeepL（需要API密钥）",
            "本批不翻译",
        ],
    )
    retry_failed = st.checkbox(
        "仅重试之前失败的词",
        value=False,
    )
    force_overwrite = st.checkbox(
        "强制重新查询并覆盖自动补全字段",
        value=False,
        help="不会改变单词、中文释义、词性等原始字段；"
             "但会重查音标并重译例句。",
    )

provider_mapping = {
    "MyMemory（默认，无需密钥）": "mymemory",
    "DeepL（需要API密钥）": "deepl",
    "本批不翻译": "none",
}
selected_provider = provider_mapping[provider_label]

if selected_provider == "deepl":
    st.warning(
        "请先在项目根目录的 .env 中配置 DEEPL_API_KEY。"
    )

start = st.button(
    "开始自动补全",
    type="primary",
    use_container_width=True,
)

if start:
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(index: int, total: int, word: str) -> None:
        ratio = index / total if total else 1.0
        progress_bar.progress(ratio)
        status_text.write(
            f"正在处理 {index}/{total}：{word}"
        )

    with st.spinner("正在查询词典并翻译，请不要重复点击……"):
        result = enrich_words(
            chapter=selected_chapter,
            limit=batch_size,
            fill_missing_example=fill_missing_example,
            translate_example=(
                translate_example and selected_provider != "none"
            ),
            retry_failed=retry_failed,
            force_overwrite=force_overwrite,
            translation_provider=selected_provider,
            progress_callback=update_progress,
        )

    progress_bar.progress(1.0)
    status_text.write("本批处理完成。")

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("本批处理", result["processed"])
    r2.metric("完整完成", result["completed"])
    r3.metric("部分完成", result["partial"])
    r4.metric("失败", result["failed"])

    if result["items"]:
        st.dataframe(
            pd.DataFrame(result["items"]),
            use_container_width=True,
            hide_index=True,
        )

    st.info(
        "部分完成通常表示：已获得音标，但词典没有例句；"
        "或者翻译服务暂时失败。可稍后勾选“仅重试之前失败的词”。"
    )

st.divider()
st.subheader("最近的补全记录")

with get_connection() as connection:
    rows = connection.execute(
        """
        SELECT
            word AS 单词,
            chapter AS 章节,
            uk_phonetic AS 英式音标,
            us_phonetic AS 美式音标,
            example_sentence AS 英文例句,
            example_translation AS 中文翻译,
            example_source AS 例句来源,
            translation_source AS 翻译来源,
            enrichment_status AS 状态,
            enrichment_error AS 错误,
            last_enriched_at AS 最后处理时间
        FROM words
        WHERE last_enriched_at IS NOT NULL
        ORDER BY last_enriched_at DESC
        LIMIT 100
        """
    ).fetchall()

history_df = pd.DataFrame([dict(row) for row in rows])

if history_df.empty:
    st.caption("还没有自动补全记录。")
else:
    st.dataframe(
        history_df,
        use_container_width=True,
        hide_index=True,
    )
