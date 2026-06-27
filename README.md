# IELTS Vocabulary Planner v1.3.1 Performance

这是 v1.3.1 性能优化版。

## 部署入口

Streamlit Cloud 的 Main file path 请填写：

```text
main_app/app.py
```

## Secrets

```toml
APP_MODE = "cloud"
DATABASE_URL = "postgresql+psycopg2://postgres.xxxxx:你的密码@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require"
```

## 本版优化重点

- 数据库连接池；
- 数据库初始化缓存；
- 自动创建查询索引；
- 用户学习状态同步加速；
- 我的词库分页显示；
- 学习统计数据库聚合；
- 补全中心默认小批量；
- 关闭默认自动翻译；
- 导入和预览防卡顿。

## 建议使用方式

### 导入词库

可以导入全量 Excel，但页面只预览前200行。

### 补全例句

建议先这样设置：

```text
每批处理数量：10
自动翻译英文例句：关闭
```

等英文例句补得差不多后，再打开翻译小批量补。

### 词库查看

“我的词库”已分页，几千词也不会一次性加载。
