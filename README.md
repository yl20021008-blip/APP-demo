# IELTS Vocabulary Planner v1.3.3

这是 v1.3.3 页面状态优化版。

## 主要优化

- 顶部状态栏：当前学习者、数据库状态、版本号；
- 侧边栏状态：登录状态、数据库模式、刷新按钮；
- 首页根据当前状态自动提示下一步；
- 页面出错时更容易截图排查；
- 关键页面增加操作影响说明。

## 部署入口

Streamlit Cloud 的 Main file path 必须填写：

```text
main_app/app.py
```

## Secrets

```toml
APP_MODE = "cloud"
DATABASE_URL = "postgresql+psycopg2://postgres.xxxxx:你的密码@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
```

## 使用建议

- 词库导入后先进入“今日学习”测试；
- 词汇补全每批 10 个；
- 自动翻译先关闭；
- 大词库查看使用分页。
