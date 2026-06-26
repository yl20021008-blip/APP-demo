from __future__ import annotations

import html

import streamlit as st

from modules.database import init_database
from modules.review_service import get_today_queue, submit_review
from modules.settings_service import get_setting, set_setting

st.set_page_config(
    page_title="今日学习",
    page_icon="🧠",
    layout="centered",
)
init_database()

st.title("🧠 今日学习")

with st.expander("今日任务设置", expanded=False):
    current_new_limit = int(get_setting("daily_new_limit", "20"))
    daily_new_limit_input = st.number_input(
        "每日新词数量",
        min_value=0,
        max_value=100,
        value=current_new_limit,
        step=5,
    )
    if st.button("保存设置"):
        set_setting(
            "daily_new_limit",
            str(int(daily_new_limit_input)),
        )
        for key in (
            "study_queue",
            "study_index",
            "show_answer",
            "completed_count",
        ):
            st.session_state.pop(key, None)
        st.success("设置已保存。")
        st.rerun()

daily_new_limit = int(get_setting("daily_new_limit", "20"))
daily_review_limit = int(get_setting("daily_review_limit", "200"))

if "study_queue" not in st.session_state:
    st.session_state.study_queue = get_today_queue(
        daily_new_limit=daily_new_limit,
        daily_review_limit=daily_review_limit,
    )
    st.session_state.study_index = 0
    st.session_state.show_answer = False
    st.session_state.completed_count = 0

queue = st.session_state.study_queue
index = st.session_state.study_index

if not queue:
    st.success(
        "今天没有待完成任务。可以上传新章节，或等待下一次复习。"
    )
    st.stop()

if index >= len(queue):
    st.success(
        f"今日任务完成，共完成 "
        f"{st.session_state.completed_count} 个单词。"
    )
    if st.button("检查10分钟后再次到期的词"):
        st.session_state.study_queue = get_today_queue(
            daily_new_limit=0,
            daily_review_limit=daily_review_limit,
        )
        st.session_state.study_index = 0
        st.session_state.show_answer = False
        st.rerun()
    st.stop()

current = queue[index]
st.progress(index / len(queue))
st.caption(f"进度：{index + 1} / {len(queue)}")

task_name = (
    "到期复习"
    if current["task_type"] == "review"
    else "今日新词"
)
st.markdown(
    f"**任务类型：{task_name}｜章节："
    f"{html.escape(str(current['chapter']))}**"
)

word_text = html.escape(str(current["word"]))
pos_text = html.escape(str(current.get("part_of_speech") or ""))

st.markdown(
    f"""
<div style="
    padding: 28px;
    border: 1px solid #d9d9d9;
    border-radius: 16px;
    text-align: center;
    margin-top: 12px;
    margin-bottom: 18px;
">
    <div style="font-size: 42px; font-weight: 700;">
        {word_text}
    </div>
    <div style="font-size: 18px; margin-top: 8px;">
        {pos_text}
    </div>
</div>
""",
    unsafe_allow_html=True,
)

phonetic_parts = []
if current.get("uk_phonetic"):
    phonetic_parts.append(
        f"英 /{str(current['uk_phonetic']).strip('/')} /"
    )
if current.get("us_phonetic"):
    phonetic_parts.append(
        f"美 /{str(current['us_phonetic']).strip('/')} /"
    )
if phonetic_parts:
    st.markdown("　　".join(phonetic_parts))

audio_col1, audio_col2 = st.columns(2)
if current.get("uk_audio_url"):
    with audio_col1:
        st.caption("英式发音")
        st.audio(current["uk_audio_url"], format="audio/mpeg")
if current.get("us_audio_url"):
    with audio_col2:
        st.caption("美式发音")
        st.audio(current["us_audio_url"], format="audio/mpeg")

if not st.session_state.show_answer:
    if st.button(
        "显示答案",
        type="primary",
        use_container_width=True,
    ):
        st.session_state.show_answer = True
        st.rerun()
else:
    st.subheader("释义")
    st.write(current.get("annotation") or "暂无释义")

    if current.get("expansion"):
        st.subheader("派生词")
        st.write(current["expansion"])

    if current.get("collocation"):
        st.subheader("固定搭配")
        st.write(current["collocation"])

    if current.get("example_sentence"):
        st.subheader("例句")
        st.write(current["example_sentence"])

        if current.get("example_translation"):
            st.caption("例句翻译")
            st.write(current["example_translation"])

        source_parts = []
        if current.get("example_source"):
            source_parts.append(
                f"例句：{current['example_source']}"
            )
        if current.get("translation_source"):
            source_parts.append(
                f"翻译：{current['translation_source']}"
            )
        if source_parts:
            st.caption("｜".join(source_parts))

    st.divider()
    st.caption("请选择你刚才真实的回忆结果。")

    col1, col2, col3, col4 = st.columns(4)
    result = None

    if col1.button("忘记", use_container_width=True):
        result = "忘记"
    if col2.button("模糊", use_container_width=True):
        result = "模糊"
    if col3.button("正确", use_container_width=True):
        result = "正确"
    if col4.button("熟练", use_container_width=True):
        result = "熟练"

    if result:
        submit_review(
            word_id=int(current["id"]),
            result=result,
        )
        st.session_state.study_index += 1
        st.session_state.completed_count += 1
        st.session_state.show_answer = False
        st.rerun()
