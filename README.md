# IELTS Vocabulary Planner v1.3

这是 v1.3 云端保存 + 用户区分 + 故事优化 + 例句自动补充版。

## 重要部署设置

Streamlit Cloud 的 Main file path 请填写：

```text
main_app/app.py
```

## Streamlit Secrets

在 Streamlit Cloud 里设置：

```toml
DATABASE_URL = "你的 Supabase PostgreSQL 连接字符串"
APP_MODE = "cloud"
```

不要把 DATABASE_URL 放进 GitHub。

## v1.3 新增重点

### 故事记忆优化

- 场景路线式故事；
- 加粗目标词；
- 中文释义线索；
- 自动复习小测；
- 每个用户独立保存故事。

### 例句自动补充

补全顺序：

```text
上传词库自带例句
→ 词典 API 真实例句
→ 本地生成雅思学习例句
→ 自动翻译
```

如果词典查不到例句，系统会自动生成适合背词的英文句子，并标记来源：

```text
local_generated_ielts_example
```

## 仍然保留的功能

- Supabase/PostgreSQL 云端保存；
- 学习者名称 + PIN；
- 公共词库共享；
- 每个人独立学习进度；
- 每个人独立复习计划；
- 每个人独立学习统计；
- 批量 Excel/CSV 导入；
- phonetic 音标字段导入；
- 自定义侧边栏导航。
