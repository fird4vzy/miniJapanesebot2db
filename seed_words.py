"""
Loads words_seed.json into the `words` table of japanese_bot.db.

This is what makes a fresh deploy possible: bot.py's init_db() creates the
empty schema, and this script fills it with the curated vocabulary from the
repository. Together they mean a brand-new VPS can be brought up from git
alone, with no hand-built database.

Usage on a fresh box:

    source venv/bin/activate
    python3 -c "import bot"      # not needed; init_db runs on bot startup
    python3 seed_words.py

Idempotent: uses INSERT OR IGNORE against the UNIQUE constraint on `word`,
so re-running never duplicates or overwrites existing rows. Words already in
the DB are left exactly as they are — this only fills in what's missing.
"""
import json
import os
import sqlite3

DB_NAME = 'japanese_bot.db'
SEED_FILE = 'words_seed.json'

COLUMNS = [
    "word", "level", "romaji", "en_meaning", "ru_meaning",
    "example_jp", "example_romaji", "example_en", "example_ru",
]


def ensure_schema(cur):
    """Same DDL as bot.py's init_db, so this script works standalone."""
    cur.execute('''
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT UNIQUE,
            level TEXT,
            romaji TEXT,
            en_meaning TEXT,
            ru_meaning TEXT,
            example_jp TEXT,
            example_romaji TEXT,
            example_en TEXT,
            example_ru TEXT
        )
    ''')
    cur.execute("CREATE INDEX IF NOT EXISTS idx_words_level ON words(level)")


def main():
    if not os.path.exists(SEED_FILE):
        print(f"❌ {SEED_FILE} not found. Run export_words.py on a box that "
              f"has the populated database, and commit the result.")
        return

    with open(SEED_FILE, encoding='utf-8') as f:
        rows = json.load(f)

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    ensure_schema(cur)

    cur.execute("SELECT COUNT(*) FROM words")
    before = cur.fetchone()[0]

    placeholders = ", ".join("?" * len(COLUMNS))
    cur.executemany(
        f"INSERT OR IGNORE INTO words ({', '.join(COLUMNS)}) VALUES ({placeholders})",
        [tuple(r.get(c) for c in COLUMNS) for r in rows]
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM words")
    after = cur.fetchone()[0]
    conn.close()

    print(f"✅ Seeded from {SEED_FILE}: {after - before} new words inserted "
          f"({before} → {after} total; {len(rows) - (after - before)} already present).")


if __name__ == "__main__":
    main()
