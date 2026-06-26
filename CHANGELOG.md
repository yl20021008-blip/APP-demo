# Changelog

## v1.2.2 No Auto Pages Hotfix

- 修复 Streamlit Cloud 自动扫描 `pages/` 目录时出现的 `StreamlitAPIException` 页面导航错误。
- 新主入口改为 `main_app/app.py`。
- 页面文件移至 `app_pages/`，由自定义侧边栏导航手动加载。
- 新增 `runtime.txt`，固定 Python 3.11，避免云端使用过新的 Python 版本导致兼容问题。
- 固定 Streamlit 到稳定版本范围 `>=1.39,<1.50`。
- 保留 v1.2 的云端数据库、学习者名称 + PIN、公共词库共享、独立学习进度、批量导入、音标导入、故事记忆功能。
