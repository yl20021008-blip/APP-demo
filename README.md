# IELTS Vocabulary Planner v1.5

这是 v1.5 莫兰迪科研风 + 底部常用导航版。

## 结构调整

### 底部常用导航

```text
首页 / 今日学习 / 复习计划 / 故事记忆 / 学习统计
```

### 左侧词库与管理

```text
我的词库 / 上传词库 / 批量导入 / 词汇补全 / 公共词库管理
```

## 色调

采用低饱和莫兰迪科研风：

- 米灰背景；
- 鼠尾草绿主色；
- 低饱和棕灰；
- 柔和卡片；
- 更统一的字体与按钮。

## 部署入口

Streamlit Cloud 的 Main file path 必须是：

```text
main_app/app.py
```

## Secrets

```toml
APP_MODE = "cloud"
DATABASE_URL = "postgresql+psycopg2://..."
ADMIN_PIN = "你自己的管理员PIN"
PUBLIC_WORDLIST_LOCKED = "true"
```
