"""
One-off migration: moves per-user level preference out of settings.json
and into the `level` column of the `users` table in japanese_bot.db.

Run this ONCE on the VPS, after pulling the updated bot.py but before
(or right after) restarting the service:

    source venv/bin/activate
    python3 migrate_level_to_db.py

Safe to re-run — it only overwrites the level for users present in
settings.json and leaves everyone else untouched. After confirming it
worked (see printed summary), settings.json can be deleted.
"""
import json
import os
import sqlite3

DB_NAME = 'japanese_bot.db'
SETTINGS_FILE = 'settings.json'


def main():
    if not os.path.exists(SETTINGS_FILE):
        print(f"No {SETTINGS_FILE} found — nothing to migrate.")
        return

    with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
        settings = json.load(f)

    if not settings:
        print(f"{SETTINGS_FILE} is empty — nothing to migrate.")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Make sure the column exists (bot.py's init_db() also does this,
    # but this script can be run standalone too).
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row[1] for row in cursor.fetchall()}
    if "level" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN level TEXT DEFAULT 'N5'")

    migrated = 0
    for user_id_str, level in settings.items():
        user_id = int(user_id_str)
        cursor.execute(
            "INSERT INTO users (user_id, level) VALUES (?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET level = excluded.level",
            (user_id, level)
        )
        migrated += 1

    conn.commit()
    conn.close()
    print(f"✅ Migrated level preference for {migrated} user(s) into {DB_NAME}.")
    print(f"You can now delete {SETTINGS_FILE} (git rm --cached it too — see cleanup_repo.sh).")


if __name__ == "__main__":
    main()
