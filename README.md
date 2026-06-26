# IELTS Vocabulary Planner

这是一个基于 Streamlit 的雅思词汇学习 Demo APP。

## 功能

- Excel 词库导入；
- 我的词库管理；
- 自动补全音标、发音、缺失例句与例句翻译；
- 今日新词与到期复习；
- 间隔重复复习；
- 学习统计；
- 30词故事记忆。

## 本地运行

```powershell
python -m pip install -r requirements.txt
python check_env.py
python upgrade_check.py
python -m streamlit run app.py
```

打开：

```text
http://localhost:8501
```

## Streamlit Cloud 部署

1. 将本文件夹上传到 GitHub；
2. 在 Streamlit Cloud 选择“从 GitHub 部署一个公共应用”；
3. Repository 选择你的仓库；
4. Branch 选择 `main`；
5. Main file path 填写：

```text
app.py
```

6. 点击 Deploy。

## 不要上传的内容

`.gitignore` 已经排除：

```text
.venv/
.env
database/*.db
database/backups/
.idea/
__pycache__/
```

## Demo 版说明

当前版本使用 SQLite 本地数据库。部署到 Streamlit Cloud 后，适合展示与体验，但不建议作为长期保存学习记录的正式线上数据库。

如果要长期在线使用，建议下一步改为：

```text
Streamlit + Supabase/PostgreSQL
```

## 翻译配置

默认使用 MyMemory，无需密钥。

如果使用 DeepL，请复制：

```text
.env.example
```

为：

```text
.env
```

并填写：

```text
TRANSLATION_PROVIDER=deepl
DEEPL_API_KEY=你的DeepL密钥
DEEPL_USE_FREE=true
```
