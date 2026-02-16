import sqlite3
import json
import os


def migrate_to_db():
    # 1. Setup Database Connection
    conn = sqlite3.connect('japanese_bot.db')
    cursor = conn.cursor()

    # Create the users table if it doesn't exist yet
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            level_pref TEXT DEFAULT 'N5',
            language_pref TEXT DEFAULT 'en',
            xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_seen DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Migrate Subscribers (subscribers.json)
    if os.path.exists('subscribers.json'):
        try:
            with open('subscribers.json', 'r') as f:
                subs = json.load(f)
                # Handle if subs is a list [123, 456] or a dict {"123": ...}
                user_ids = subs if isinstance(subs, list) else subs.keys()

                for user_id in user_ids:
                    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (int(user_id),))
            print(f"✅ Migrated {len(user_ids)} subscribers to Database.")
        except Exception as e:
            print(f"⚠️ Could not migrate subscribers: {e}")

    # 3. Migrate Settings (settings.json)
    if os.path.exists('settings.json'):
        try:
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                for user_id, data in settings.items():
                    # Check if data is a dict like {"level": "N4"} or just a string "N4"
                    if isinstance(data, dict):
                        level = data.get('level', 'N5')
                    else:
                        level = data  # It's just the string "N4"

                    cursor.execute('''
                        UPDATE users SET level_pref = ? WHERE user_id = ?
                    ''', (level, int(user_id)))
            print("✅ Migrated user settings to Database.")
        except Exception as e:
            print(f"⚠️ Could not migrate settings: {e}")

    conn.commit()
    conn.close()
    print("🏁 Migration finished successfully.")


if __name__ == "__main__":
    migrate_to_db()