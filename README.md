# IELTS Vocabulary Planner v1.2.1

这是一个 Streamlit + Supabase/PostgreSQL 的雅思词汇学习 APP。

## 核心功能

- 云端数据库保存；
- 学习者名称 + PIN 区分用户；
- 公共词库共享；
- 每个学习者独立学习进度；
- 每个学习者独立复习计划；
- 批量导入 Excel / CSV；
- 导入时识别 phonetic / uk_phonetic / us_phonetic；
- 自动补全音标、发音、例句和翻译；
- 故事记忆。

## Streamlit Cloud 设置

Main file path：

```text
app.py
```

Secrets：

```toml
DATABASE_URL = "postgresql://postgres.xxxxx:你的密码@xxxxx.pooler.supabase.com:6543/postgres"
APP_MODE = "cloud"
```

不要把 DATABASE_URL 写入 GitHub。

## v1.2.1 修复

为避免 Streamlit Cloud 在多页面导航初始化时对中文页面文件名处理不稳定，本版将 `pages/` 内文件名改为英文路径；页面内部标题仍然是中文。
