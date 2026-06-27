from __future__ import annotations

import html
import uuid

import streamlit as st
import streamlit.components.v1 as components


def render_pronunciation_controls(
    word: str,
    uk_audio_url: str | None = None,
    us_audio_url: str | None = None,
    uk_phonetic: str | None = None,
    us_phonetic: str | None = None,
) -> None:
    """显示读音控件。

    优先使用词典真实音频 URL；如果没有 URL，则使用浏览器 SpeechSynthesis TTS 兜底。
    这样即使导入词库只有 phonetic 字段，也能点击播放读音。
    """
    clean_word = str(word or "").strip()
    if not clean_word:
        return

    st.markdown("#### 读音")
    phonetic_parts = []
    if uk_phonetic:
        phonetic_parts.append(f"英 /{str(uk_phonetic).strip('/')} /")
    if us_phonetic:
        phonetic_parts.append(f"美 /{str(us_phonetic).strip('/')} /")
    if phonetic_parts:
        st.caption("　　".join(phonetic_parts))
    else:
        st.caption("暂无音标，仍可使用浏览器朗读。")

    audio_col1, audio_col2 = st.columns(2)

    with audio_col1:
        if uk_audio_url:
            st.caption("英式词典音频")
            st.audio(uk_audio_url, format="audio/mpeg")
        else:
            _render_tts_button(clean_word, "en-GB", "播放英式读音")

    with audio_col2:
        if us_audio_url:
            st.caption("美式词典音频")
            st.audio(us_audio_url, format="audio/mpeg")
        else:
            _render_tts_button(clean_word, "en-US", "播放美式读音")


def _render_tts_button(text: str, lang: str, label: str) -> None:
    safe_text = html.escape(text, quote=True)
    safe_lang = html.escape(lang, quote=True)
    safe_label = html.escape(label, quote=True)
    element_id = f"tts_{uuid.uuid4().hex}"

    components.html(
        f"""
        <div style="margin: 4px 0 12px 0;">
          <button
            id="{element_id}"
            style="
              width: 100%;
              border: 1px solid #d9e2ef;
              background: #ffffff;
              border-radius: 12px;
              padding: 10px 12px;
              font-size: 14px;
              cursor: pointer;
              color: #27364a;
            "
          >🔊 {safe_label}</button>
        </div>
        <script>
          const btn = document.getElementById("{element_id}");
          btn.addEventListener("click", function() {{
            const utterance = new SpeechSynthesisUtterance("{safe_text}");
            utterance.lang = "{safe_lang}";
            utterance.rate = 0.82;
            utterance.pitch = 1.0;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utterance);
          }});
        </script>
        """,
        height=58,
    )
