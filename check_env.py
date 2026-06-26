from __future__ import annotations
import platform, sqlite3, sys
from importlib.metadata import PackageNotFoundError, version
PACKAGES = ['streamlit', 'pandas', 'openpyxl', 'plotly', 'sqlalchemy', 'psycopg2-binary', 'requests', 'python-dotenv']
print('='*60); print('IELTS Vocabulary App v1.2 环境检查'); print('='*60)
print(f'操作系统：{platform.platform()}'); print(f'Python：{sys.version.split()[0]}'); print(f'解释器路径：{sys.executable}'); print(f'SQLite：{sqlite3.sqlite_version}'); print('-'*60)
for package in PACKAGES:
    try: package_version = version(package)
    except PackageNotFoundError: package_version = '未安装'
    print(f'{package:16s}: {package_version}')
print('='*60)
