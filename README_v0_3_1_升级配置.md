# v0.3.1 原地升级与配置

## 一、升级前

在 PyCharm 终端按：

```powershell
Ctrl + C
```

停止当前 APP。

然后运行：

```powershell
python backup_database.py
```

若当前项目还没有备份脚本，请手动复制：

```text
database\vocabulary.db
```

到其他安全位置。

## 二、覆盖更新

把本更新包解压后的全部文件，复制到原项目文件夹：

```text
IELTS_Vocabulary_App_Starter
```

Windows 提示时选择替换或合并。

更新包不包含：

- `.venv`
- `database\vocabulary.db`
- `.env`

因此不会覆盖虚拟环境和学习数据。

## 三、安装新增依赖

在原项目 PyCharm 终端运行：

```powershell
python -m pip install -r requirements.txt
```

## 四、配置翻译服务

### 方案A：MyMemory，无需密钥

这是默认方案。不创建 `.env` 也可以直接运行。

也可以复制：

```text
.env.example
```

并改名为：

```text
.env
```

保持：

```text
TRANSLATION_PROVIDER=mymemory
```

### 方案B：DeepL

把 `.env.example` 复制为 `.env`，填写：

```text
TRANSLATION_PROVIDER=deepl
DEEPL_API_KEY=你的DeepL密钥
DEEPL_USE_FREE=true
```

不要把真实密钥发给别人，也不要提交到公开仓库。

## 五、执行数据库升级

运行：

```powershell
python upgrade_check.py
```

看到：

```text
升级检查：通过。
```

即可。

## 六、启动

```powershell
python -m streamlit run app.py
```

左侧应出现：

```text
词汇补全中心
```

## 七、第一次补全

1. 打开“词汇补全中心”；
2. 选择 Chapter 13；
3. 每批先设为 5 或 10；
4. 保持“补充词典例句”和“自动翻译英文例句”勾选；
5. 翻译服务选择 MyMemory；
6. 点击“开始自动补全”；
7. 检查结果后再继续下一批。

## 八、补全原则

- 原书已有英文例句不会被覆盖；
- 原书无例句时，才采用词典例句；
- 已有中文翻译默认不会被覆盖；
- 接口失败不会删除旧内容；
- 失败记录可以在以后单独重试；
- 所有补全结果都会保存到原 vocabulary.db。

## 九、常见问题

### 缺少 requests 或 dotenv

运行：

```powershell
python -m pip install -r requirements.txt
```

### 翻译暂时失败

MyMemory 可能临时限流。稍后勾选：

```text
仅重试之前失败的词
```

再处理。

### 某些词没有例句

公开词典并不是每个词都提供例句。这类词会显示“部分完成”，不会生成不可靠的伪例句。

### 学习页面没有立即显示新内容

刷新页面，或在终端按 `Ctrl + C` 后重新启动 APP。
