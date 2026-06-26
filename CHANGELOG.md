# 更新记录

## v1.2.0 Cloud User

- 新增 Supabase / PostgreSQL 云数据库支持；
- 保留本地 SQLite fallback；
- 新增学习者名称 + PIN 登录；
- 公共词库共享，不同学习者学习进度独立；
- 重构学习状态表为 user_id + word_id；
- 复习记录、统计、故事记忆按学习者独立保存；
- 保留 v1.1 的音标字段导入、批量导入和词汇补全功能；
- 适配 Streamlit Cloud Secrets：DATABASE_URL。
