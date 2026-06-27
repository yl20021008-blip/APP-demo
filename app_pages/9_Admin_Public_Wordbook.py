from __future__ import annotations

import streamlit as st
from sqlalchemy import func, select

from modules.admin_service import (
    admin_login,
    admin_logout,
    clear_public_wordbook,
    delete_chapter,
    export_wordbook_excel_bytes,
    get_admin_pin,
    get_chapter_summary,
    get_public_edit_locked,
    import_preset_wordbook,
    is_admin,
    reset_to_preset_wordbook,
    sync_all_users_learning_status,
    try_create_helpful_indexes,
)
from modules.auth_ui import require_login
from modules.database import get_connection, init_database, users, words

init_database()
user_id, display_name = require_login()

st.title("🛡️ 公共词库管理")
st.caption("管理员专用：预设公共词库、锁定普通用户编辑、删除错误章节、导出备份。")

locked = get_public_edit_locked()
admin_pin_configured = bool(get_admin_pin())

col_a, col_b, col_c = st.columns(3)
with get_connection() as conn:
    total_words = conn.execute(select(func.count()).select_from(words)).scalar_one()
    total_users = conn.execute(select(func.count()).select_from(users)).scalar_one()

col_a.metric("公共词库词数", int(total_words or 0))
col_b.metric("学习者数量", int(total_users or 0))
col_c.metric("公共词库状态", "已锁定" if locked else "未锁定")

if not admin_pin_configured:
    st.error("还没有配置 ADMIN_PIN。请在 Streamlit Secrets 里添加 ADMIN_PIN。")
    st.code('ADMIN_PIN = "你自己的管理员PIN"\nPUBLIC_WORDLIST_LOCKED = "true"', language="toml")
    st.stop()

if not is_admin():
    st.warning("你当前不是管理员。普通学习者只能学习公共词库，不能编辑公共词库。")
    pin = st.text_input("管理员 PIN", type="password")
    if st.button("进入管理员模式", type="primary"):
        if admin_login(pin):
            st.success("管理员登录成功。")
            st.rerun()
        else:
            st.error("管理员 PIN 不正确。")
    st.stop()

st.success(f"管理员模式已开启。当前账号：{display_name}")

if st.button("退出管理员模式"):
    admin_logout()
    st.rerun()

st.divider()

tab_overview, tab_preset, tab_delete, tab_export, tab_settings = st.tabs(
    ["词库概览", "预设词库", "删除/清理", "导出备份", "设置说明"]
)

with tab_overview:
    st.subheader("章节概览")
    summary = get_chapter_summary()
    if summary.empty:
        st.info("当前公共词库为空。")
    else:
        st.dataframe(summary, use_container_width=True, hide_index=True)

    if st.button("同步所有学习者学习状态"):
        added = sync_all_users_learning_status()
        st.success(f"同步完成，新增学习状态记录：{added}")

    if st.button("创建/修复常用索引"):
        try_create_helpful_indexes()
        st.success("索引检查完成。")

with tab_preset:
    st.subheader("一键导入预设公共词库")
    st.info("这个版本已内置 data/default_wordbook.xlsx。管理员可以一键导入或重置为预设词库。")

    update_existing = st.checkbox("如果已有同词，自动补齐缺失字段", value=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("导入预设词库，不清空现有词库", type="primary", use_container_width=True):
            try:
                result = import_preset_wordbook(update_existing=update_existing)
                st.success(
                    f"导入完成：新增 {result['inserted']}，补齐 {result['updated']}，重复 {result['duplicated']}，同步学习状态 {result['synced_learning_status']}。"
                )
            except Exception as exc:
                st.error(f"导入失败：{exc}")

    with col2:
        confirm_reset = st.text_input("输入 RESET 确认清空并重置为预设词库")
        if st.button("清空公共词库并重置为预设词库", use_container_width=True):
            if confirm_reset != "RESET":
                st.error("请先输入 RESET。")
            else:
                try:
                    result = reset_to_preset_wordbook()
                    st.success(
                        f"已重置：删除旧词 {result['deleted_words']}，新增 {result['inserted']}，补齐 {result['updated']}，同步学习状态 {result['synced_learning_status']}。"
                    )
                except Exception as exc:
                    st.error(f"重置失败：{exc}")

with tab_delete:
    st.subheader("删除错误章节 / 清空公共词库")
    summary = get_chapter_summary()
    if summary.empty:
        st.info("当前没有可删除章节。")
    else:
        chapter = st.selectbox("选择要删除的章节", options=summary["章节"].tolist())
        confirm = st.text_input("输入 DELETE 确认删除所选章节")
        if st.button("删除所选章节"):
            if confirm != "DELETE":
                st.error("请先输入 DELETE。")
            else:
                deleted = delete_chapter(chapter)
                st.success(f"已删除章节：{chapter}，删除词数：{deleted}。")

    st.warning("清空公共词库会删除所有公共单词、学习状态、复习记录和故事。")
    confirm_all = st.text_input("输入 CLEAR_ALL 确认清空全部公共词库")
    if st.button("清空全部公共词库"):
        if confirm_all != "CLEAR_ALL":
            st.error("请先输入 CLEAR_ALL。")
        else:
            result = clear_public_wordbook()
            st.success(f"清空完成：删除词数 {result['deleted_words']}，学习状态 {result['deleted_learning_status']}，复习记录 {result['deleted_review_logs']}。")

with tab_export:
    st.subheader("导出公共词库备份")
    st.caption("建议每次大改词库前先导出备份。")
    try:
        excel_bytes = export_wordbook_excel_bytes()
        st.download_button(
            "下载公共词库备份 Excel",
            data=excel_bytes,
            file_name="public_wordbook_backup.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    except Exception as exc:
        st.error(f"生成备份失败：{exc}")

with tab_settings:
    st.subheader("推荐 Secrets 设置")
    st.code(
        'APP_MODE = "cloud"\nDATABASE_URL = "postgresql+psycopg2://..."\nADMIN_PIN = "你自己的管理员PIN"\nPUBLIC_WORDLIST_LOCKED = "true"',
        language="toml",
    )
    st.markdown(
        """
        - `ADMIN_PIN`：管理员进入公共词库管理页的 PIN。
        - `PUBLIC_WORDLIST_LOCKED = "true"`：普通学习者不能上传、批量导入、补全公共词库。
        - 普通学习者仍然可以学习、复习、查看词库、生成自己的故事。
        """
    )
