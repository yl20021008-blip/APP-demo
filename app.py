from __future__ import annotations

import streamlit as st

from modules.auth_ui import render_login_box
from modules.database import get_dashboard_metrics, get_database_mode, init_database
from modules.settings_service import get_setting

st.set_page_config(page_title='IELTS Vocabulary Planner', page_icon='📘', layout='wide')
init_database()

st.title('📘 IELTS Vocabulary Planner')
st.caption('云端保存 + 学习者区分版：公共词库共享，每个人的学习进度独立保存。')

user_id = st.session_state.get('user_id')
display_name = st.session_state.get('display_name')

if not user_id:
    st.info('请先登录或创建学习者。第一次使用只需要输入一个名称和4位以上 PIN。')
    render_login_box(location='main')
else:
    st.success(f'当前学习者：{display_name}')
    if st.button('退出当前学习者'):
        st.session_state.pop('user_id', None)
        st.session_state.pop('display_name', None)
        st.rerun()

metrics = get_dashboard_metrics(int(user_id)) if user_id else get_dashboard_metrics(None)
daily_new_limit = int(get_setting('daily_new_limit', '20'))

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric('公共词库总量', metrics['total_words'])
col2.metric('今日到期复习', metrics['due_reviews'])
col3.metric('我的待学新词', metrics['new_words'])
col4.metric('我的已学词', metrics['learned_words'])
col5.metric('学习者数量', metrics['total_users'])

st.caption(f'数据库模式：{get_database_mode()}')
st.divider()
st.subheader('使用顺序')
st.markdown("""
1. 先在首页创建/登录学习者；
2. 进入 **上传词库** 或 **批量导入词库**，导入公共词库；
3. 进入 **词汇补全中心**，补全缺失音标、发音、例句和翻译；
4. 进入 **今日学习**，每个人的学习进度会独立保存；
5. 背完约30个词后，进入 **故事记忆** 生成自己的记忆故事。
""")
