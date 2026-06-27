# IELTS Vocabulary Planner v1.4

这是 v1.4 公共词库管理版。

## 解决的问题

之前所有用户都能上传、批量导入、补全公共词库，容易导致公共词库混乱。

现在改成：

```text
管理员维护公共词库
普通学习者只学习、复习、生成自己的故事
```

## 新增页面

```text
🛡️ 公共词库管理
```

管理员可以：

- 一键导入预设词库；
- 一键重置为预设词库；
- 删除错误章节；
- 清空公共词库；
- 导出公共词库 Excel 备份；
- 同步所有学习者学习状态；
- 创建/修复常用索引。

## 必须设置 Secrets

在 Streamlit Cloud 的 Secrets 中加入：

```toml
APP_MODE = "cloud"
DATABASE_URL = "postgresql+psycopg2://..."
ADMIN_PIN = "你自己的管理员PIN"
PUBLIC_WORDLIST_LOCKED = "true"
```

## 使用流程

1. 管理员进入首页登录学习者账号；
2. 进入 `🛡️ 公共词库管理`；
3. 输入管理员 PIN；
4. 一键导入或重置预设词库；
5. 普通用户进入后直接学习，不再编辑公共词库。

## 部署入口

Streamlit Cloud 的 Main file path 必须是：

```text
main_app/app.py
```
