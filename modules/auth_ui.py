from __future__ import annotations

import streamlit as st

from modules.auth_service import login_or_create_user
from modules.database import get_database_mode, init_database


def render_login_box(location: str = 'main') -> None:
    init_database()
    target = st.sidebar if location == 'sidebar' else st
    target.subheader('👤 学习者登录')
    display_name = target.text_input('学习者名称', key=f'{location}_login_name', placeholder='例如 Jasmine')
    pin = target.text_input('4位以上PIN', type='password', key=f'{location}_login_pin')
    create_if_missing = target.checkbox('第一次使用时自动创建学习者', value=True, key=f'{location}_create_user')
    if target.button('进入学习', type='primary', use_container_width=True, key=f'{location}_login_btn'):
        try:
            user = login_or_create_user(display_name, pin, create_if_missing=create_if_missing)
        except Exception as exc:  # noqa: BLE001
            target.error(str(exc))
        else:
            st.session_state['user_id'] = user['id']
            st.session_state['display_name'] = user['display_name']
            target.success(f'已进入：{user["display_name"]}')
            st.rerun()


def require_login() -> tuple[int, str]:
    init_database()
    mode = get_database_mode()
    st.sidebar.caption(f'数据库模式：{mode}')
    if st.session_state.get('user_id'):
        st.sidebar.success(f'当前学习者：{st.session_state.get("display_name", "未命名")}')
        if st.sidebar.button('退出当前学习者'):
            st.session_state.pop('user_id', None)
            st.session_state.pop('display_name', None)
            st.rerun()
        return int(st.session_state['user_id']), str(st.session_state.get('display_name', ''))

    render_login_box(location='sidebar')
    st.warning('请先在左侧输入学习者名称和 PIN。第一次使用会自动创建学习者。')
    st.stop()
