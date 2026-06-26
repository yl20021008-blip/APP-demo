# IELTS Vocabulary Planner v1.2

这是云端保存 + 学习者区分版。

## 主要功能

- Supabase / PostgreSQL 云数据库保存；
- 本地 SQLite fallback；
- 学习者名称 + PIN 区分用户；
- 公共词库共享；
- 每个人独立学习进度、复习计划、学习统计和故事记忆；
- 支持 Excel / CSV 单文件导入；
- 支持多文件批量导入；
- 支持 phonetic / 音标字段导入；
- 支持自动补全音标、发音、例句和翻译。

## Streamlit Cloud Secrets

在 Streamlit Cloud 的 App 页面进入：

```text
Settings → Secrets
```

填写：

```toml
DATABASE_URL = "postgresql://postgres.xxxxx:你的密码@aws-xxx.pooler.supabase.com:6543/postgres"
APP_MODE = "cloud"
```

不要把 DATABASE_URL 写入 GitHub。

## 部署设置

```text
Repository: 你的用户名/APP-demo
Branch: main
Main file path: app.py
```

## 本地运行

不配置 DATABASE_URL 时，会自动使用本地 SQLite。

```powershell
python -m pip install -r requirements.txt
python upgrade_check.py
python -m streamlit run app.py
```

## 用户逻辑

- 词库 `words` 是公共的；
- 学习者表 `users` 用名称 + PIN 创建；
- 每个学习者的 `learning_status`、`review_logs`、`story_groups` 独立保存；
- 当前 PIN 方案适合 Demo 和小范围试用，后续可升级 Supabase Auth 邮箱登录。
