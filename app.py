# Fallback entry.
# 推荐在 Streamlit Cloud 中把 Main file path 设置为：main_app/app.py
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).resolve().parent / "main_app" / "app.py"), run_name="__main__")
