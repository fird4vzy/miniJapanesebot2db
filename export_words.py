"""
Dumps the `words` table from japanese_bot.db into words_seed.json.

Why this exists: japanese_bot.db is (correctly) gitignored, so the curated
vocabulary currently lives ONLY on the VPS disk. If that droplet dies, the
words are gone. words_seed.json puts them back under version control.

Run on the VPS after adding new words, then commit the result:

    source venv/bin/activate
    python3 export_words.py
    git add words_seed.json
    git commit -m "Update word seed"
    git push origin main

Pair with seed_words.py, which loads this file into a fresh database.
"""
import json
import sqlite3

DB_NAME = 'japanese_bot.db'
SEED_FILE = 'words_seed.json'

COLUMNS = [
    "word", "level", "romaji", "en_meaning", "ru_meaning",
    "example_jp", "example_romaji", "example_en", "example_ru",
]


def main():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # id is deliberately not exported — it's a local autoincrement value,
    # not part of the content, and exporting it would create pointless
    # diffs whenever rows are re-inserted.
    cur.execute(f"SELECT {', '.join(COLUMNS)} FROM words ORDER BY level, word")
    rows = [dict(row) for row in cur.fetchall()]
    conn.close()

    with open(SEED_FILE, 'w', encoding='utf-8') as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
        f.write("\n")

    by_level = {}
    for r in rows:
        by_level[r["level"]] = by_level.get(r["level"], 0) + 1

    print(f"✅ Exported {len(rows)} words to {SEED_FILE}")
    for level in sorted(by_level):
        print(f"   {level}: {by_level[level]}")
    print("Now commit words_seed.json so the vocabulary lives in git.")


if __name__ == "__main__":
    main()
