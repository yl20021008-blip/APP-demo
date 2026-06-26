# IELTS Vocabulary Planner v1.2.2

这是 v1.2.2 云端保存 + 用户区分热修复版。

## 重要部署设置

Streamlit Cloud 的 Main file path 请填写：

```text
main_app/app.py
```

不是：

```text
app.py
```

这样可以绕开 Streamlit Cloud 自动扫描根目录 `pages/` 目录时出现的页面导航报错。

## 上传 GitHub 前建议

如果你的旧仓库里已经有 `pages/` 文件夹，建议在本地仓库里删除它，再复制本版本文件。

当前版本使用：

```text
app_pages/
main_app/app.py
```

不再依赖 Streamlit 自动多页面系统。

## Streamlit Secrets

在 Streamlit Cloud 里设置：

```toml
DATABASE_URL = "你的 Supabase PostgreSQL 连接字符串"
APP_MODE = "cloud"
```

不要把 DATABASE_URL 放进 GitHub。

## 功能

- Supabase / PostgreSQL 云端保存
- 学习者名称 + PIN
- 公共词库共享
- 每个人独立学习进度
- 每个人独立复习计划
- 每个人独立学习统计
- 每个人独立故事记忆
- 批量导入 Excel / CSV
- 支持 phonetic / 音标字段导入
