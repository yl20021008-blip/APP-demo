from __future__ import annotations

import shutil
from pathlib import Path

from modules.database import init_database

ROOT = Path(__file__).resolve().parent
example_env = ROOT / ".env.example"
real_env = ROOT / ".env"

init_database()

if not real_env.exists() and example_env.exists():
    shutil.copy2(example_env, real_env)
    print("已创建 .env，默认使用无需密钥的 MyMemory 翻译。")
else:
    print(".env 已存在，未覆盖。")

print("v0.3.1 数据库配置完成。")
print("下一步运行：python upgrade_check.py")
