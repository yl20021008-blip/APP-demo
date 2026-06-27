# Changelog

## v1.4.0 Admin Public Wordbook

本版本解决“公共词库大家都能编辑，容易混乱”的问题。

### 新增

1. 公共词库管理页：`🛡️ 公共词库管理`
2. 公共词库锁定：普通学习者不能上传、批量导入、补全公共词库
3. 预设公共词库：内置 `data/default_wordbook.xlsx`
4. 管理员可以一键导入或重置为预设词库
5. 管理员可以按章节删除、清空公共词库、导出备份
6. 管理员可以同步所有学习者学习状态

### 需要新增 Streamlit Secrets

```toml
ADMIN_PIN = "你自己的管理员PIN"
PUBLIC_WORDLIST_LOCKED = "true"
```

### 部署入口

Streamlit Cloud 的 Main file path 仍然是：

```text
main_app/app.py
```
