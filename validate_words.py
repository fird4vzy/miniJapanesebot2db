"""
Checks every word in japanese_bot.db for the kinds of damage that are easy
to introduce when adding vocabulary by hand and hard to notice afterwards.

It looks for:
  * stray characters — Hangul, Cyrillic or Latin sitting inside a Japanese
    field (a real thing that has happened: 十人以上집まりました)
  * kanji or kana leaking into the Russian/English meaning fields
  * empty or missing fields
  * words whose level isn't one the bot offers
  * duplicate words

Run it on the VPS after every vocabulary batch:

    source venv/bin/activate
    python3 validate_words.py

Exit code is 0 when clean, 1 when something needs fixing, so it can be
wired into a pre-deploy check later if you want.
"""
import sqlite3
import sys
import unicodedata

DB_NAME = 'japanese_bot.db'
KNOWN_LEVELS = {"N5", "N4", "N3", "N2", "N1"}

JP_FIELDS = ["word", "example_jp"]
LATIN_FIELDS = ["romaji", "example_romaji", "en_meaning", "example_en"]
RU_FIELDS = ["ru_meaning", "example_ru"]
ALL_FIELDS = JP_FIELDS + LATIN_FIELDS + RU_FIELDS

PUNCT = set(" 、。！？「」（）・～ー－,.!?()%:;'\"-—/0123456789　")


def is_kana(cp):
    return 0x3040 <= cp <= 0x30FF


def is_kanji(cp):
    # Main block plus Extension A, which holds rarer characters.
    return 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF


def is_jp_punctuation(cp):
    """CJK Symbols and Punctuation, U+3000-U+303F.

    This block holds ordinary Japanese writing marks that an earlier
    version of this checker wrongly flagged — most notably 々 (U+3005),
    the kanji iteration mark in 別々, 色々 and 少々, which are all
    perfectly correct Japanese.
    """
    return 0x3000 <= cp <= 0x303F


def is_hangul(cp):
    return 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF


def is_cyrillic(cp):
    return 0x0400 <= cp <= 0x04FF


def check_japanese(text):
    """Japanese fields: kana, kanji, punctuation and incidental Latin only."""
    bad = []
    for ch in text:
        cp = ord(ch)
        if ch in PUNCT or ch.isspace():
            continue
        if is_kana(cp) or is_kanji(cp) or is_jp_punctuation(cp):
            continue
        if 0xFF00 <= cp <= 0xFFEF:  # fullwidth forms
            continue
        if ch.isascii() and ch.isalpha():
            continue
        bad.append(ch)
    return bad


def check_latin(text):
    """Romaji/English fields shouldn't contain CJK or Cyrillic."""
    return [ch for ch in text
            if is_kana(ord(ch)) or is_kanji(ord(ch))
            or is_hangul(ord(ch)) or is_cyrillic(ord(ch))]


def check_russian(text):
    """Russian fields shouldn't contain CJK or Hangul."""
    return [ch for ch in text
            if is_kana(ord(ch)) or is_kanji(ord(ch)) or is_hangul(ord(ch))]


def describe(chars):
    return ", ".join(f"{c!r} ({unicodedata.name(c, 'unknown')})" for c in dict.fromkeys(chars))


def main():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(f"SELECT id, level, {', '.join(ALL_FIELDS)} FROM words ORDER BY id")
    rows = cur.fetchall()
    conn.close()

    if not rows:
        print("No words in the database.")
        return 1

    problems = []
    seen = {}

    for row in rows:
        word = row["word"]

        for field in ALL_FIELDS:
            value = row[field]
            if value is None or not str(value).strip():
                problems.append((word, field, "empty", ""))
                continue
            value = str(value)

            if field in JP_FIELDS:
                bad = check_japanese(value)
            elif field in LATIN_FIELDS:
                bad = check_latin(value)
            else:
                bad = check_russian(value)

            if bad:
                problems.append((word, field, describe(bad), value))

        if row["level"] not in KNOWN_LEVELS:
            problems.append((word, "level", f"unknown level {row['level']!r}", ""))

        if word in seen:
            problems.append((word, "word", f"duplicate (also id {seen[word]})", ""))
        else:
            seen[word] = row["id"]

    by_level = {}
    for row in rows:
        by_level[row["level"]] = by_level.get(row["level"], 0) + 1

    print(f"Checked {len(rows)} words")
    for level in sorted(by_level, reverse=True):
        print(f"   {level}: {by_level[level]}")
    print()

    if not problems:
        print("✅ No problems found.")
        return 0

    print(f"❌ {len(problems)} problem(s):\n")
    for word, field, issue, value in problems:
        print(f"  {word}  .{field}")
        print(f"      {issue}")
        if value:
            print(f"      value: {value}")
    print()
    print("Fix these with sqlite3, e.g.:")
    print("  sqlite3 japanese_bot.db \"UPDATE words SET example_jp='...' WHERE word='...';\"")
    return 1


if __name__ == "__main__":
    sys.exit(main())
