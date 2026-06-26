# IELTS Vocabulary App MVP v0.2

## 当前已完成

- Excel 章节导入
- SQLite 词库
- 词库筛选和导出
- 每日新词任务
- 到期复习任务
- 忘记 / 模糊 / 正确 / 熟练反馈
- 自动计算下一次复习时间
- 未来复习计划
- 学习统计和薄弱词识别

## 首次运行

```powershell
python -m pip install -r requirements.txt
python check_env.py
python -m streamlit run app.py
```

## 旧版本数据迁移

如果你已经在旧版本导入过词汇，建议先保留旧项目作为备份。

最稳妥的做法是：

1. 打开新版本；
2. 重新上传原始 Excel；
3. 从新版本重新开始学习。

旧版数据库只有 words 表，而新版本还增加了 learning_status、
review_logs 和 app_settings。直接复制旧数据库可能缺少新表或字段。

## 每天使用

1. 打开 PyCharm；
2. 在终端运行 `python -m streamlit run app.py`；
3. 进入“今日学习”；
4. 完成到期复习；
5. 完成今日新词；
6. 在“复习计划”和“学习统计”查看结果；
7. 结束时在终端按 `Ctrl + C`。

## 下一阶段建议

- 拼写输入题
- 中译英测试
- 例句填空
- 音标和发音
- 每日打卡日历
- 用户登录
- FastAPI 接口
- 微信小程序前端
