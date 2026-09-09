"""
Pre-generates pronunciation audio for every word in the database.

Why: audio is now part of the word message itself, so the FIRST time any
word is shown the user waits a second or two while it's synthesized. This
script does all of that work up front, so every word is instant from then
on.

It uploads each clip to a chat you own, records the file_id, and deletes
the message. Telegram keeps file_ids valid after deletion, so the chat
stays clean.

Usage on the VPS:

    source venv/bin/activate
    python3 prewarm_audio.py <your_telegram_user_id>

Find your user id by messaging @userinfobot on Telegram, or read it from
the bot's own database:

    sqlite3 japanese_bot.db "SELECT user_id FROM users;"

Safe to re-run: words that already have cached audio are skipped, so you
can run it again after adding new vocabulary.
"""
import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Telegram allows roughly one message per second per chat. Going faster
# earns a 429 and a forced wait, so pace deliberately.
DELAY_SECONDS = 1.2


async def main(chat_id):
    token = os.getenv("BOT_TOKEN")
    if not token:
        print("❌ BOT_TOKEN not set. Put it in a .env file next to this script.")
        return 1

    # Imported here, not at module level: bot.py refuses to load without a
    # token, and that error would otherwise hide the usage message below.
    from telegram import Bot
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import bot as botmod

    botmod.init_db()
    words = botmod.load_words()
    if not words:
        print("❌ No words in the database. Run seed_words.py first.")
        return 1

    todo = [w["word"] for w in words if not botmod.get_cached_audio(w["word"])]
    done_already = len(words) - len(todo)

    print(f"Words in DB:      {len(words)}")
    print(f"Already cached:   {done_already}")
    print(f"To generate:      {len(todo)}")
    if not todo:
        print("\n✅ Nothing to do — every word already has audio.")
        return 0
    print(f"Estimated time:   ~{int(len(todo) * (DELAY_SECONDS + 1) / 60) + 1} min\n")

    tg = Bot(token)
    ok = failed = 0

    async with tg:
        for i, word in enumerate(todo, 1):
            try:
                file_id = await botmod._get_or_make_audio(_Ctx(tg), chat_id, word)
                if file_id:
                    ok += 1
                    print(f"[{i}/{len(todo)}] ✅ {word}")
                else:
                    failed += 1
                    print(f"[{i}/{len(todo)}] ❌ {word} (no audio produced)")
            except Exception as e:
                failed += 1
                print(f"[{i}/{len(todo)}] ❌ {word} — {type(e).__name__}: {e}")

            await asyncio.sleep(DELAY_SECONDS)

    print(f"\nDone. Cached: {ok}, failed: {failed}")
    if failed:
        print("Re-run the script to retry just the failures.")
    return 0


class _Ctx:
    """Minimal stand-in for the PTB context object _get_or_make_audio expects."""

    def __init__(self, bot):
        self.bot = bot


if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].lstrip("-").isdigit():
        print(__doc__)
        print("Usage: python3 prewarm_audio.py <your_telegram_user_id>")
        sys.exit(1)
    sys.exit(asyncio.run(main(int(sys.argv[1]))) or 0)
