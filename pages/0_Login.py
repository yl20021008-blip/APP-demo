from __future__ import annotations
import streamlit as st
from modules.auth_ui import render_login_box
from modules.database import get_database_mode, init_database

st.set_page_config(page_title='学习者登录', page_icon='👤', layout='centered')
init_database()
st.title('👤 学习者登录')
st.caption('同一个公共词库，不同学习者的进度互不影响。')
if st.session_state.get('user_id'):
    st.success(f'已登录：{st.session_state.get("display_name")}')
    st.caption(f'数据库模式：{get_database_mode()}')
    if st.button('退出登录'):
        st.session_state.pop('user_id', None)
        st.session_state.pop('display_name', None)
        st.rerun()
else:
    render_login_box(location='main')
st.info('提示：PIN 不是正式安全认证，只适合 Demo 和小范围试用。后续可升级成邮箱登录。')
