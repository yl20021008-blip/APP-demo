from __future__ import annotations
import pandas as pd
import streamlit as st
from modules.auth_ui import require_login
from modules.database import init_database
from modules.story_service import count_available_story_words, create_next_story, delete_story, get_next_story_words, get_story_detail, list_stories
init_database(); user_id, display_name = require_login()
st.title('📖 故事记忆')
st.caption('故事是每个学习者独立保存的。')
available_count = count_available_story_words(user_id); stories = list_stories(user_id)
col1, col2, col3 = st.columns(3); col1.metric('可生成故事的已学词', available_count); col2.metric('我的已生成故事', len(stories)); col3.metric('默认分组', '30词/组')
st.divider()
with st.expander('下一组将使用哪些词', expanded=False):
    preview_words = get_next_story_words(user_id, 30)
    if not preview_words: st.info('暂无可进入故事的已学词。先去“今日学习”完成新词。')
    else: st.dataframe(pd.DataFrame([{'序号': idx+1, '单词': item['word'], '词性': item.get('part_of_speech'), '释义': item.get('annotation'), '章节': item.get('chapter')} for idx, item in enumerate(preview_words)]), use_container_width=True, hide_index=True)
left, right = st.columns(2)
with left:
    group_size = st.number_input('每组单词数量', min_value=5, max_value=50, value=30, step=5)
    allow_partial = st.checkbox('不足一组时也生成测试故事', value=False)
with right:
    style = st.selectbox('故事风格', options=['IELTS memory story', 'campus life', 'city walk', 'architecture journey', 'travel diary'], index=0)
if st.button('生成下一组记忆故事', type='primary', use_container_width=True):
    result = create_next_story(user_id, group_size=int(group_size), allow_partial=allow_partial, style=style)
    if result['created']:
        st.success(f'已生成第 {result["group_number"]} 组故事：{result["title_zh"]}，共 {result["word_count"]} 个词。'); st.rerun()
    else: st.warning(result['reason'])
st.divider(); st.subheader('我的故事列表')
stories = list_stories(user_id)
if not stories:
    st.info('还没有故事。完成30个新词后即可生成第一篇。'); st.stop()
story_options = {f'第 {s["group_number"]} 组｜{s["title_zh"]}｜{s["word_count"]}词': s['id'] for s in stories}
selected_label = st.selectbox('选择故事', options=list(story_options.keys()))
selected_story_id = story_options[selected_label]
detail = get_story_detail(user_id, selected_story_id)
if detail is None: st.error('没有找到该故事。'); st.stop()
story = detail['story']; items = detail['items']
st.markdown(f'## {story["title_zh"]}'); st.caption(f'{story["title_en"]}｜{story["word_count"]}词｜{story["provider"]}｜{story["created_at"]}')
tab_cn, tab_en, tab_words = st.tabs(['中文故事', 'English Story', '故事词表'])
with tab_cn:
    st.markdown(story['story_zh'])
    if story.get('memory_tip'): st.info(story['memory_tip'])
with tab_en: st.markdown(story['story_en'])
with tab_words:
    st.dataframe(pd.DataFrame([{'顺序': item['position'], '单词': item['word'], '词性': item.get('part_of_speech'), '英式音标': item.get('uk_phonetic'), '美式音标': item.get('us_phonetic'), '释义': item.get('annotation'), '英文情节': item.get('sentence_en'), '中文情节': item.get('sentence_zh')} for item in items]), use_container_width=True, hide_index=True)
with st.expander('危险操作：删除这个故事'):
    st.warning('删除故事后，这组单词会重新回到你的故事队列。')
    if st.button('删除当前故事'):
        delete_story(user_id, selected_story_id); st.success('已删除。'); st.rerun()
