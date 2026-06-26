from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT / "database" / "vocabulary.db"
BACKUP_DIR = ROOT / "database" / "backups"

if not DATABASE.exists():
    print("未找到 database/vocabulary.db，无需备份。")
else:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"vocabulary_{timestamp}.db"
    shutil.copy2(DATABASE, target)
    print(f"备份完成：{target}")
