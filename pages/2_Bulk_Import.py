from __future__ import annotations
import pandas as pd
import streamlit as st
from modules.auth_ui import require_login
from modules.database import init_database
from modules.importer import import_words, infer_chapter_from_filename, read_uploaded_file

st.set_page_config(page_title='批量导入词库', page_icon='📂', layout='wide')
init_database()
user_id, display_name = require_login()
st.title('📂 批量导入词库')
st.caption('一次上传多个 Excel / CSV，系统自动用文件名或表内 Chapter 列识别章节。')
book_name = st.text_input('词汇书名称', value='雅思词汇真经')
update_existing = st.checkbox('重复词自动补齐旧记录缺失字段', value=True)
uploaded_files = st.file_uploader('选择多个词库文件', type=['xlsx', 'xls', 'csv'], accept_multiple_files=True)
if not uploaded_files:
    st.info('可以一次选择多个章节文件，或直接上传全量词库 Excel。')
    st.stop()
parsed_items, errors = [], []
for uploaded_file in uploaded_files:
    try:
        df = read_uploaded_file(uploaded_file)
        fallback_chapter = infer_chapter_from_filename(uploaded_file.name)
        phonetic_count = int((df['uk_phonetic'].fillna('').astype(str).str.strip().ne('') | df['us_phonetic'].fillna('').astype(str).str.strip().ne('')).sum())
        parsed_items.append({'file_name': uploaded_file.name, 'fallback_chapter': fallback_chapter, 'df': df, 'word_count': len(df), 'chapter_count': df['chapter'].dropna().nunique() or 1, 'phonetic_count': phonetic_count})
    except Exception as exc:
        errors.append({'文件名': uploaded_file.name, '错误': str(exc)})
summary_df = pd.DataFrame([{'文件名': i['file_name'], '默认章节名': i['fallback_chapter'], '有效词数': i['word_count'], '表内章节数': i['chapter_count'], '已有音标数': i['phonetic_count']} for i in parsed_items])
if not summary_df.empty:
    st.subheader('读取预览')
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
if errors:
    st.subheader('读取失败文件')
    st.dataframe(pd.DataFrame(errors), use_container_width=True, hide_index=True)
col1, col2, col3 = st.columns(3)
col1.metric('成功读取文件', len(parsed_items)); col2.metric('读取失败文件', len(errors)); col3.metric('合计有效词条', int(summary_df['有效词数'].sum()) if not summary_df.empty else 0)
with st.expander('抽样预览前50个词', expanded=False):
    if parsed_items:
        sample = pd.concat([item['df'].assign(来源文件=item['file_name']) for item in parsed_items], ignore_index=True).head(50)
        st.dataframe(sample, use_container_width=True, hide_index=True)
if parsed_items and st.button('确认批量导入公共词库', type='primary', use_container_width=True):
    rows, total_inserted, total_updated, total_duplicated = [], 0, 0, 0
    progress = st.progress(0)
    for index, item in enumerate(parsed_items, start=1):
        progress.progress(index / len(parsed_items))
        try:
            result = import_words(item['df'], chapter=item['fallback_chapter'], book_name=book_name, update_existing=update_existing, user_id=user_id)
            total_inserted += result['inserted']; total_updated += result['updated']; total_duplicated += result['duplicated']
            rows.append({'文件名': item['file_name'], '新增': result['inserted'], '补齐旧记录': result['updated'], '重复': result['duplicated'], '状态': '成功'})
        except Exception as exc:
            rows.append({'文件名': item['file_name'], '新增': 0, '补齐旧记录': 0, '重复': 0, '状态': f'失败：{exc}'})
    st.success(f'批量导入完成：新增 {total_inserted} 个，补齐旧记录 {total_updated} 个，重复 {total_duplicated} 个。')
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
