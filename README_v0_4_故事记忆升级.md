# v0.4 故事记忆功能升级说明

## 升级步骤

1. 停止当前 APP：

```powershell
Ctrl + C
```

2. 备份数据库：

```powershell
python backup_database.py
```

3. 解压更新包，将全部文件复制到原项目文件夹：

```text
IELTS_Vocabulary_App_Starter
```

4. 安装依赖：

```powershell
python -m pip install -r requirements.txt
```

5. 检查升级：

```powershell
python upgrade_check.py
```

看到：

```text
升级检查：通过。
```

即可启动：

```powershell
python -m streamlit run app.py
```

## 使用方式

1. 先在“今日学习”完成至少30个新词；
2. 进入“故事记忆”；
3. 打开“下一组将使用哪些词”，检查单词；
4. 点击“生成下一组记忆故事”；
5. 在“中文故事 / English Story / 故事词表”之间切换查看；
6. 复习时先回忆故事路线，再回忆对应单词。

## 说明

v0.4 默认使用本地模板生成故事，不需要 API，不会产生费用。  
后续可以把 `modules/story_service.py` 中的 `build_local_story()` 替换为 AI 生成器。
