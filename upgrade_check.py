from __future__ import annotations

from modules.database import DB_PATH, get_connection, init_database

init_database()

required_word_columns = {
    "uk_phonetic", "us_phonetic", "uk_audio_url", "us_audio_url",
    "example_translation", "example_source", "translation_source",
    "enrichment_status", "enrichment_error", "enrichment_attempts",
    "last_enriched_at",
}

required_tables = {
    "words", "learning_status", "review_logs", "app_settings",
    "story_groups", "story_group_items",
}

with get_connection() as connection:
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(words)").fetchall()}
    existing_tables = {
        row["name"] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    word_count = connection.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    status_count = connection.execute("SELECT COUNT(*) FROM learning_status").fetchone()[0]
    story_count = connection.execute("SELECT COUNT(*) FROM story_groups").fetchone()[0]

missing_columns = sorted(required_word_columns - columns)
missing_tables = sorted(required_tables - existing_tables)

print("=" * 68)
print("IELTS Vocabulary App v0.4 故事记忆升级检查")
print("=" * 68)
print(f"数据库位置：{DB_PATH}")
print(f"words：{word_count}")
print(f"learning_status：{status_count}")
print(f"story_groups：{story_count}")

if missing_columns:
    print("缺少自动补全字段：")
    for name in missing_columns:
        print(f"  - {name}")
else:
    print("自动补全字段：完整")

if missing_tables:
    print("缺少数据表：")
    for name in missing_tables:
        print(f"  - {name}")
else:
    print("核心数据表：完整")

if not missing_columns and not missing_tables and word_count == status_count:
    print("升级检查：通过。")
else:
    print("升级检查：未通过，请保留终端信息。")
print("=" * 68)
