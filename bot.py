import asyncio
import datetime
import hashlib
import json
import logging
import os
import random
import shutil
import sqlite3  # Added SQLite
import tempfile

from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.error import BadRequest, Forbidden
from telegram.helpers import escape_markdown
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)

from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN is not set. Create a .env file with BOT_TOKEN=<your token> "
        "next to bot.py (see .env.example)."
    )
DB_NAME = 'japanese_bot.db'  # Switched to DB

# Levels the bot offers, in learning order. Add a tuple here (and words at
# that level in the DB) to introduce N2/N1 — the settings menu, the daily
# job and the quiz all read from this list, so nothing else needs editing.
LEVELS = [
    ("N5", "Beginner"),
    ("N4", "Elementary"),
    ("N3", "Intermediate"),
]
VALID_LEVELS = [code for code, _ in LEVELS]
SUBSCRIBERS_FILE = 'subscribers.json'

# --- LOGGING SETUP ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


# --- DATABASE FUNCTIONS ---

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates missing tables/columns. Safe to run every startup."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_active_date TEXT
        )
    ''')
    cursor.execute("PRAGMA table_info(users)")
    existing_columns = {row["name"] for row in cursor.fetchall()}
    if "level" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN level TEXT DEFAULT 'N5'")
    if "lang" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN lang TEXT")

    # The words table used to exist only because it was hand-created in
    # DB Browser. Declaring it here means a fresh VPS can rebuild the schema
    # from this repo alone. Matches the schema the live DB already uses.
    cursor.execute('''
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
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_words_level ON words(level)")

    # Maps a piece of Japanese text to the Telegram file_id of its audio.
    # Once a word has been voiced once, every later playback reuses the
    # file_id — no TTS call, no upload, no local file.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audio_cache (
            text_hash TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            file_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    ''')

    # Remembers which daily words each subscriber has already received, so
    # the daily pick can avoid repeats until their level is exhausted.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sent_words (
            user_id INTEGER NOT NULL,
            word TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            PRIMARY KEY (user_id, word)
        )
    ''')

    conn.commit()
    conn.close()


def count_words_by_level():
    """{'N5': 200, 'N4': 262, ...} — used to show sizes in the settings menu."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT level, COUNT(*) AS n FROM words GROUP BY level")
    counts = {row["level"]: row["n"] for row in cursor.fetchall()}
    conn.close()
    return counts


def load_words(level=None):
    """Fetches words from the database instead of JSON."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if level:
        cursor.execute("SELECT * FROM words WHERE level = ?", (level,))
    else:
        cursor.execute("SELECT * FROM words")
    rows = cursor.fetchall()
    conn.close()

    # Convert SQLite rows to dictionary format to match your existing logic
    words_list = []
    for row in rows:
        words_list.append({
            "word": row["word"],
            "level": row["level"],
            "romaji": row["romaji"],
            "en_meaning": row["en_meaning"],
            "ru_meaning": row["ru_meaning"],
            "example": {
                "jp": row["example_jp"],
                "romaji": row["example_romaji"],
                "en": row["example_en"],
                "ru": row["example_ru"]
            }
        })
    return words_list


def get_user_stats(user_id):
    """Fetches XP and Streak from the DB."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT xp, streak, last_active_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row if row else {"xp": 0, "streak": 0, "last_active_date": None}


def save_score_and_streak(user_id, points):
    """Updates XP and calculates Streak."""
    conn = get_db_connection()
    cursor = conn.cursor()

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    cursor.execute("SELECT xp, streak, last_active_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if not row:
        # New user entry
        new_xp = points
        new_streak = 1
        cursor.execute("INSERT INTO users (user_id, xp, streak, last_active_date) VALUES (?, ?, ?, ?)",
                       (user_id, new_xp, new_streak, today.isoformat()))
    else:
        new_xp = row['xp'] + points
        last_active = datetime.date.fromisoformat(row['last_active_date']) if row['last_active_date'] else None

        if last_active == yesterday:
            new_streak = row['streak'] + 1
        elif last_active == today:
            new_streak = row['streak']
        else:
            new_streak = 1  # Streak reset

        cursor.execute("UPDATE users SET xp = ?, streak = ?, last_active_date = ? WHERE user_id = ?",
                       (new_xp, new_streak, today.isoformat(), user_id))

    conn.commit()
    conn.close()
    return new_xp, new_streak


# --- DATA FUNCTIONS (JSON based) ---

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, 'r') as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()


def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, 'w') as f:
        json.dump(list(subs), f)


def get_user_level(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT level FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["level"] if row and row["level"] else 'N5'


def save_user_setting(user_id, level):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, level) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET level = excluded.level",
        (user_id, level)
    )
    conn.commit()
    conn.close()


# --- HELPER FUNCTIONS ---

def format_word_message(word_data, lang="ru"):
    level = word_data.get('level', 'N5')
    example = word_data.get("example", {})
    # Both translations stay on the card on purpose: the labels follow the
    # interface language, but a learner benefits from seeing both meanings.
    msg = (
        f"{t('w_level', lang)} {level}\n"
        f"{t('w_word', lang)} {word_data['word']}\n"
        f"{t('w_romaji', lang)} {word_data['romaji']}\n"
        f"{t('w_english', lang)} {word_data['en_meaning']}\n"
        f"{t('w_russian', lang)} {word_data['ru_meaning']}\n\n"
        f"{t('w_example', lang)}\n"
        f"🇯🇵: {example.get('jp', '-')}\n"
        f"📖: {example.get('romaji', '-')}\n"
        f"🇬🇧: {example.get('en', '-')}\n"
        f"🇷🇺: {example.get('ru', '-')}"
    )
    return msg


def get_keyboard(lang="ru"):
    keyboard = [
        [InlineKeyboardButton(t("btn_random", lang), callback_data='random')],
        [InlineKeyboardButton(t("btn_quiz", lang), callback_data='quiz_start')],
        [InlineKeyboardButton(t("btn_settings", lang), callback_data='settings_menu')],
        [InlineKeyboardButton(t("btn_subscribe", lang), callback_data='subscribe')],
        [InlineKeyboardButton(t("btn_unsubscribe", lang), callback_data='unsubscribe')]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- AUDIO / PRONUNCIATION ---

# Which text-to-speech backend to use: "edge" (Microsoft neural voices,
# better Japanese) or "gtts" (Google Translate). Both are free but
# unofficial, so if one starts failing, switch with the TTS_ENGINE env var
# instead of editing code.
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge").lower()
TTS_VOICE = os.getenv("TTS_VOICE", "ja-JP-NanamiNeural")


# --- LOCALISATION ---

# Every user-facing string lives here so the bot speaks one language at a
# time instead of mixing them. Add a language by adding a key to each entry
# and a tuple to UI_LANGUAGES.
UI_LANGUAGES = [("ru", "Русский"), ("en", "English")]
VALID_LANGS = [code for code, _ in UI_LANGUAGES]

STRINGS = {
    # --- main menu ---
    "btn_random":     {"ru": "🎲 Случайное слово",     "en": "🎲 Get Random Word"},
    "btn_quiz":       {"ru": "🧠 Викторина",            "en": "🧠 Take a Quiz"},
    "btn_settings":   {"ru": "⚙️ Настройки",            "en": "⚙️ Settings"},
    "btn_subscribe":  {"ru": "🔔 Подписаться (9:00)",   "en": "🔔 Subscribe (9 AM)"},
    "btn_unsubscribe":{"ru": "🔕 Отписаться",           "en": "🔕 Unsubscribe"},
    "btn_back":       {"ru": "🔙 В меню",               "en": "🔙 Back to Menu"},
    "btn_menu":       {"ru": "🏁 Меню",                 "en": "🏁 Menu"},
    "btn_next_q":     {"ru": "🔄 Следующий вопрос",     "en": "🔄 Next Question"},
    "btn_new_q":      {"ru": "🔄 Новый вопрос",         "en": "🔄 New Question"},

    # --- word card ---
    "w_level":   {"ru": "🏷 **Уровень:**",   "en": "🏷 **Level:**"},
    "w_word":    {"ru": "🇯🇵 **Слово:**",     "en": "🇯🇵 **Word:**"},
    "w_romaji":  {"ru": "📖 **Ромадзи:**",   "en": "📖 **Romaji:**"},
    "w_english": {"ru": "🇬🇧 **Английский:**","en": "🇬🇧 **English:**"},
    "w_russian": {"ru": "🇷🇺 **Русский:**",   "en": "🇷🇺 **Russian:**"},
    "w_example": {"ru": "📝 **Пример:**",     "en": "📝 **Example:**"},

    # --- start / stats ---
    "greeting":  {"ru": "Конничива, {name}! 🇯🇵",  "en": "Kon'nichiwa, {name}! 🇯🇵"},
    "streak":    {"ru": "🔥 **Серия:** {n} дн.",   "en": "🔥 **Streak:** {n} days"},
    "xp":        {"ru": "🎮 **Опыт:** {n}",        "en": "🎮 **XP:** {n} points"},
    "what_todo": {"ru": "Чем займёмся сегодня?",   "en": "What would you like to do today?"},

    # --- settings ---
    "settings_title": {"ru": "⚙️ **Настройки**",        "en": "⚙️ **Settings**"},
    "cur_level":      {"ru": "Текущий уровень: **{lvl}**", "en": "Current level: **{lvl}**"},
    "choose_level":   {"ru": "Выберите уровень сложности:", "en": "Choose your difficulty level:"},
    # Russian needs three plural forms; see plural_ru below.
    "words_forms":    {"ru": "слово|слова|слов",        "en": "word|words|words"},
    "cur_lang":       {"ru": "Язык интерфейса: **{lang}**", "en": "Interface language: **{lang}**"},
    "bad_level":      {"ru": "Неизвестный уровень.",    "en": "Unknown level."},

    # --- level names ---
    "lvl_N5": {"ru": "Начальный",  "en": "Beginner"},
    "lvl_N4": {"ru": "Базовый",    "en": "Elementary"},
    "lvl_N3": {"ru": "Средний",    "en": "Intermediate"},
    "lvl_N2": {"ru": "Выше среднего", "en": "Upper-intermediate"},
    "lvl_N1": {"ru": "Продвинутый", "en": "Advanced"},

    # --- subscription ---
    "subscribed":     {"ru": "✅ Вы подписались на слово дня в 9:00!", "en": "✅ You have subscribed to daily words at 9:00 AM!"},
    "already_sub":    {"ru": "ℹ️ Вы уже подписаны.",   "en": "ℹ️ You are already subscribed."},
    "unsubscribed":   {"ru": "❌ Вы отписались от слова дня.", "en": "❌ You have unsubscribed from daily words."},
    "not_sub":        {"ru": "ℹ️ Вы не были подписаны.", "en": "ℹ️ You were not subscribed."},
    "daily_header":   {"ru": "☀️ **Слово дня!**",       "en": "☀️ **Daily Word!**"},

    # --- quiz ---
    "quiz_q":       {"ru": "❓ **Как переводится это слово?**", "en": "❓ **How do you translate this?**"},
    "quiz_right":   {"ru": "✅ **Верно! (+10 XP)**\n🔥 Серия: {streak} дн. | 🎮 Всего опыта: {xp}",
                     "en": "✅ **Correct! (+10 XP)**\n🔥 Streak: {streak} days | 🎮 Total XP: {xp}"},
    "quiz_wrong":   {"ru": "❌ **Неверно!**\n🎮 Всего опыта: {xp}\n\nПравильный ответ: **{answer}**.",
                     "en": "❌ **Wrong!**\n🎮 Total XP: {xp}\n\nThe correct answer was **{answer}**."},
    "quiz_stale":   {"ru": "⚠️ Этот вопрос устарел. Начните новую викторину.",
                     "en": "⚠️ This question is out of date. Start a new quiz."},
    "quiz_unparsed":{"ru": "Не удалось разобрать ответ.", "en": "Couldn't read that answer."},

    # --- errors / states ---
    "empty_db":  {"ru": "📭 Словарь пока пуст. Попробуйте позже.", "en": "📭 The dictionary is empty. Please try again later."},
    "tts_busy":  {"ru": "🔊 Готовлю озвучку…",  "en": "🔊 Preparing audio…"},
    "tts_fail":  {"ru": "🔇 Озвучка сейчас недоступна. Попробуйте позже.", "en": "🔇 Audio is unavailable right now. Please try later."},
    "generic_err": {"ru": "⚠️ Что-то пошло не так. Попробуйте /start", "en": "⚠️ Something went wrong. Try /start"},

    # --- info ---
    "info": {
        "ru": ("🇯🇵 **mini Japan**\n\n"
               "Бот для изучения японских слов к экзамену JLPT "
               "(уровни N5–N3).\n\n"
               "Команды:\n"
               "/start — главное меню и статистика\n"
               "/quiz — быстрая викторина\n"
               "/settings — уровень и язык\n"
               "/info — это сообщение"),
        "en": ("🇯🇵 **mini Japan**\n\n"
               "A bot for learning Japanese vocabulary for the JLPT "
               "(levels N5–N3).\n\n"
               "Commands:\n"
               "/start — main menu and your stats\n"
               "/quiz — a quick quiz\n"
               "/settings — level and language\n"
               "/info — this message"),
    },
}


def t(key, lang, /, **kwargs):
    """Looks up a string in `lang`, falling back to English then the key.

    `key` and `lang` are positional-only (the `/`) so that a string
    containing a {key} or {lang} placeholder can't collide with these
    parameter names — t("cur_lang", "ru", lang="Русский") would otherwise
    raise TypeError at runtime.
    """
    entry = STRINGS.get(key)
    if not entry:
        logging.warning(f"Missing translation key: {key}")
        return key
    text = entry.get(lang) or entry.get("en") or key
    return text.format(**kwargs) if kwargs else text


def plural_ru(n, forms):
    """Picks the right Russian plural form: 1 слово, 2 слова, 5 слов."""
    one, few, many = forms.split("|")
    if n % 100 in (11, 12, 13, 14):
        return many
    last = n % 10
    if last == 1:
        return one
    if last in (2, 3, 4):
        return few
    return many


def words_count_label(n, lang):
    """'1 слово' / '2 слова' / '5 слов', and '1 word' / '2 words'."""
    forms = t("words_forms", lang)
    if lang == "ru":
        form = plural_ru(n, forms)
    else:
        one, many, _ = forms.split("|")
        form = one if n == 1 else many
    return f"{n} {form}"


def save_user_lang(user_id, lang):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (user_id, lang) VALUES (?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET lang = excluded.lang",
        (user_id, lang)
    )
    conn.commit()
    conn.close()


DEFAULT_LANG = "ru"


def get_user_lang(user_id, telegram_code=None):
    """The user's interface language.

    Resolves ONCE and writes the answer back. An earlier version computed a
    fallback on every call without saving it, so the answer depended on
    whether the caller happened to pass a Telegram hint: /settings (no hint)
    said Russian while /start (hint "en") said English, for the same person,
    with nothing stored either way. Persisting here means every call site
    agrees from then on.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row and row["lang"]:
        return row["lang"]

    if telegram_code:
        resolved = "ru" if telegram_code.lower().startswith("ru") else "en"
    else:
        resolved = DEFAULT_LANG
    save_user_lang(user_id, resolved)
    return resolved


def _text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:32]


def get_cached_audio(text):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_id FROM audio_cache WHERE text_hash = ?", (_text_hash(text),))
    row = cursor.fetchone()
    conn.close()
    return row["file_id"] if row else None


def save_cached_audio(text, file_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO audio_cache (text_hash, text, file_id, created_at) "
        "VALUES (?, ?, ?, ?)",
        (_text_hash(text), text, file_id, datetime.date.today().isoformat())
    )
    conn.commit()
    conn.close()


def drop_cached_audio(text):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM audio_cache WHERE text_hash = ?", (_text_hash(text),))
    conn.commit()
    conn.close()


async def _tts_to_mp3(text, mp3_path):
    """Writes speech for `text` to mp3_path. Returns True on success."""
    if TTS_ENGINE == "edge":
        import edge_tts
        communicate = edge_tts.Communicate(text, TTS_VOICE)
        await communicate.save(mp3_path)
    else:
        from gtts import gTTS
        # gTTS is synchronous and does network I/O, so it must not run on
        # the event loop or it blocks every other user's request.
        await asyncio.to_thread(lambda: gTTS(text, lang="ja").save(mp3_path))
    return os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0


async def _mp3_to_ogg(mp3_path, ogg_path):
    """Converts to OGG/OPUS, which is what Telegram voice messages require.

    Returns True on success. If ffmpeg is missing we fall back to sending
    the MP3 as an audio file instead — playable, just a less tidy bubble.
    """
    if not shutil.which("ffmpeg"):
        return False
    proc = await asyncio.create_subprocess_exec(
        "ffmpeg", "-i", mp3_path, "-c:a", "libopus", "-b:a", "32k",
        "-y", ogg_path,
        stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
    )
    await proc.communicate()
    return proc.returncode == 0 and os.path.exists(ogg_path) and os.path.getsize(ogg_path) > 0


CAPTION_LIMIT = 1024  # Telegram's cap on media captions


async def _get_or_make_audio(context, chat_id, text):
    """Returns a Telegram file_id for `text`, generating audio if needed.

    Returns None if speech can't be produced, so callers can fall back to
    a plain text message rather than showing the user nothing.
    """
    cached = get_cached_audio(text)
    if cached:
        return cached

    # Generation takes a second or two — show the recording indicator so the
    # chat doesn't just sit there looking frozen.
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.RECORD_VOICE)
    except Exception:
        pass  # cosmetic only; never let it block the actual message

    with tempfile.TemporaryDirectory() as tmp:
        mp3_path = os.path.join(tmp, "a.mp3")
        ogg_path = os.path.join(tmp, "a.ogg")
        try:
            if not await _tts_to_mp3(text, mp3_path):
                raise RuntimeError("TTS produced no audio")
        except Exception as e:
            logging.error(f"TTS failed for {text!r}: {e}")
            return None

        # Upload once to a throwaway message purely to obtain a file_id we
        # can attach to the real message. Deleting it does not invalidate
        # the file_id, so every later send is instant.
        try:
            if await _mp3_to_ogg(mp3_path, ogg_path):
                with open(ogg_path, "rb") as f:
                    tmp_msg = await context.bot.send_voice(chat_id=chat_id, voice=f,
                                                           disable_notification=True)
                file_id = tmp_msg.voice.file_id
            else:
                with open(mp3_path, "rb") as f:
                    tmp_msg = await context.bot.send_audio(chat_id=chat_id, audio=f,
                                                           disable_notification=True)
                file_id = tmp_msg.audio.file_id
        except Exception as e:
            logging.error(f"Audio upload failed for {text!r}: {e}")
            return None

    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=tmp_msg.message_id)
    except Exception:
        # Couldn't tidy up the placeholder — harmless, the real message
        # still follows.
        pass

    save_cached_audio(text, file_id)
    return file_id


async def deliver_word(context, chat_id, word_data, keyboard, prefix="", lang="ru"):
    """Sends a word as ONE message: audio player + full text + buttons.

    Telegram can't put a playable clip inside a text message, but a voice
    message can carry the text as its caption — which gives a single
    bubble instead of a text message followed by a separate voice note.
    """
    caption = prefix + format_word_message(word_data, lang)
    file_id = None
    if len(caption) <= CAPTION_LIMIT:
        file_id = await _get_or_make_audio(context, chat_id, word_data["word"])

    if file_id:
        try:
            return await context.bot.send_voice(
                chat_id=chat_id, voice=file_id, caption=caption,
                parse_mode='Markdown', reply_markup=keyboard
            )
        except BadRequest as e:
            # Stale file_id, or a caption Telegram won't accept — fall
            # through to plain text rather than dropping the word.
            logging.info(f"send_voice failed for {word_data['word']!r}: {e}")
            drop_cached_audio(word_data["word"])

    return await context.bot.send_message(
        chat_id=chat_id, text=caption, parse_mode='Markdown', reply_markup=keyboard
    )


async def send_pronunciation(update: Update, context: ContextTypes.DEFAULT_TYPE, text):
    """Sends spoken audio for `text`, generating it only the first time."""
    query = update.callback_query
    chat_id = query.message.chat_id

    cached = get_cached_audio(text)
    if cached:
        try:
            await context.bot.send_voice(chat_id=chat_id, voice=cached, caption=f"🔊 {text}")
            return
        except BadRequest:
            # Telegram file_ids can go stale; regenerate rather than fail.
            logging.info(f"Stale file_id for {text!r}; regenerating.")
            drop_cached_audio(text)

    lang = get_user_lang(query.from_user.id, getattr(query.from_user, "language_code", None))
    await query.answer(t("tts_busy", lang))

    with tempfile.TemporaryDirectory() as tmp:
        mp3_path = os.path.join(tmp, "a.mp3")
        ogg_path = os.path.join(tmp, "a.ogg")
        try:
            if not await _tts_to_mp3(text, mp3_path):
                raise RuntimeError("TTS produced no audio")
        except Exception as e:
            logging.error(f"TTS failed for {text!r}: {e}")
            await context.bot.send_message(
                chat_id=chat_id,
                text=t("tts_fail", lang)
            )
            return

        sent = None
        if await _mp3_to_ogg(mp3_path, ogg_path):
            with open(ogg_path, "rb") as f:
                sent = await context.bot.send_voice(chat_id=chat_id, voice=f, caption=f"🔊 {text}")
        else:
            with open(mp3_path, "rb") as f:
                sent = await context.bot.send_audio(chat_id=chat_id, audio=f, title=text)

    # Cache Telegram's own id so this word is never synthesized again.
    file_id = None
    if sent and sent.voice:
        file_id = sent.voice.file_id
    elif sent and sent.audio:
        file_id = sent.audio.file_id
    if file_id:
        save_cached_audio(text, file_id)


# --- SETTINGS MENU ---

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id
        send = query.message.edit_text
    else:
        user_id = update.effective_user.id
        send = update.message.reply_text

    current_level = get_user_level(user_id)
    lang = get_user_lang(user_id, getattr(update.effective_user, "language_code", None))
    counts = count_words_by_level()
    lang_name = dict(UI_LANGUAGES).get(lang, lang)

    text = (
        f"{t('settings_title', lang)}\n\n"
        f"{t('cur_level', lang, lvl=current_level)}\n"
        f"{t('cur_lang', lang, lang=lang_name)}\n\n"
        f"{t('choose_level', lang)}"
    )

    # One row per level, built from LEVELS so adding N2/N1 needs no edit here.
    # The word count is shown so an empty level is obvious before it's picked.
    keyboard = []
    for code, _ in LEVELS:
        mark = '✅ ' if current_level == code else ''
        label = t(f"lvl_{code}", lang)
        n = words_count_label(counts.get(code, 0), lang)
        keyboard.append([InlineKeyboardButton(
            f"{mark}{code} ({label}) — {n}",
            callback_data=f'set_{code}'
        )])

    keyboard.append([
        InlineKeyboardButton(f"{'✅ ' if lang == code else ''}{name}",
                             callback_data=f'lang_{code}')
        for code, name in UI_LANGUAGES
    ])
    keyboard.append([InlineKeyboardButton(t("btn_back", lang), callback_data='menu_main')])

    await send(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    stats = get_user_stats(user_id)
    xp = stats['xp'] if isinstance(stats, sqlite3.Row) else 0
    streak = stats['streak'] if isinstance(stats, sqlite3.Row) else 0

    # first_name is user-controlled. Unescaped, a name containing _ * ` or [
    # makes Telegram reject the whole message, so /start would silently do
    # nothing for that person forever.
    safe_name = escape_markdown(user.first_name or "", version=1)
    lang = get_user_lang(user_id, getattr(user, "language_code", None))

    text = (
        f"{t('greeting', lang, name=safe_name)}\n\n"
        f"{t('streak', lang, n=streak)}\n"
        f"{t('xp', lang, n=xp)}\n\n"
        f"{t('what_todo', lang)}"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=get_keyboard(lang), parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(text, reply_markup=get_keyboard(lang), parse_mode='Markdown')


async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    lang = get_user_lang(user.id, getattr(user, "language_code", None))
    await update.message.reply_text(t("info", lang), parse_mode='Markdown')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_level = get_user_level(user_id)
    lang = get_user_lang(user_id, getattr(query.from_user, "language_code", None))

    if query.data == 'random':
        words = load_words(user_level)  # Uses level preference
        if not words:
            words = load_words()  # fall back to all levels
        if not words:
            # Empty DB (e.g. a fresh deploy before seed_words.py has run).
            await query.message.reply_text(
                t("empty_db", lang),
                reply_markup=get_keyboard(lang)
            )
            return
        # Uses the same shuffle bag as the daily word rather than a bare
        # random.choice, which has no memory and happily repeats a word you
        # just saw. Sharing one bag across both also means the morning word
        # won't echo something you pulled up yourself an hour earlier.
        random_word = pick_unseen_word(user_id, user_level) or random.choice(words)
        await deliver_word(context, query.message.chat_id, random_word,
                           get_keyboard(lang), lang=lang)

    elif query.data == 'quiz_start':
        await start_quiz(update, context)

    elif query.data.startswith('quiz_'):
        await handle_quiz_answer(update, context)

    elif query.data == 'settings_menu':
        await settings_menu(update, context)

    elif query.data.startswith('say_'):
        # Audio is now attached to the word message itself, so nothing new
        # renders this button — but messages already sitting in people's
        # chat history still have it, and it should keep working.
        await send_pronunciation(update, context, query.data.split('_', 1)[1])

    elif query.data.startswith('lang_'):
        new_lang = query.data[len('lang_'):]
        if new_lang in VALID_LANGS:
            save_user_lang(user_id, new_lang)
        await settings_menu(update, context)

    elif query.data.startswith('set_'):
        new_level = query.data[len('set_'):]
        if new_level not in VALID_LEVELS:
            await query.answer(t("bad_level", lang), show_alert=True)
            return
        save_user_setting(user_id, new_level)
        await settings_menu(update, context)

    elif query.data == 'subscribe':
        subscribers = load_subscribers()
        if user_id not in subscribers:
            subscribers.add(user_id)
            save_subscribers(subscribers)
            await query.message.reply_text(t("subscribed", lang))
        else:
            await query.message.reply_text(t("already_sub", lang))

    elif query.data == 'unsubscribe':
        subscribers = load_subscribers()
        if user_id in subscribers:
            subscribers.remove(user_id)
            save_subscribers(subscribers)
            await query.message.reply_text(t("unsubscribed", lang))
        else:
            await query.message.reply_text(t("not_sub", lang))

    elif query.data == 'menu_main':
        await start(update, context)


# --- QUIZ ---

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        user_id = query.from_user.id

        if query.message.text is not None:
            # A plain text question: edit it in place, which keeps the chat tidy.
            send = query.message.edit_text
        else:
            # The previous answer was a VOICE message with a caption.
            # edit_text can't touch media (Telegram: "there is no text in the
            # message to edit"), and editing the caption would leave the old
            # word's audio attached to a new question. Replace it instead.
            async def send(text, **kwargs):
                try:
                    await query.message.delete()
                except Exception:
                    pass  # too old to delete; a new message below is still fine
                return await context.bot.send_message(
                    chat_id=query.message.chat_id, text=text, **kwargs
                )
    else:
        user_id = update.effective_user.id
        send = update.message.reply_text

    user_level = get_user_level(user_id)
    lang = get_user_lang(user_id, getattr(update.effective_user, "language_code", None))

    # Fetch words from DB based on level
    filtered_words = load_words(user_level)
    if not filtered_words:
        filtered_words = load_words()  # fallback to all if level list is empty
    if not filtered_words:
        await send(t("empty_db", lang))
        return

    correct_word = random.choice(filtered_words)

    # Create wrong options
    available_wrongs = [w for w in filtered_words if w['word'] != correct_word['word']]
    # Safety: check if we have enough words to sample
    sample_size = min(len(available_wrongs), 3)
    wrong_options = random.sample(available_wrongs, sample_size)

    options = [correct_word] + wrong_options
    random.shuffle(options)

    keyboard = []
    for opt in options:
        is_right = "correct" if opt['word'] == correct_word['word'] else "wrong"
        # The button displays English + Russian meaning together
        # One language per button: showing both makes the buttons unreadable.
        label = opt['ru_meaning'] if lang == 'ru' else opt['en_meaning']
        keyboard.append(
            [InlineKeyboardButton(label, callback_data=f"quiz_{is_right}_{correct_word['word']}")])

    # --- FORMATTED TEXT TO MATCH YOUR IMAGE ---
    # This uses the exact emojis and layout from image_1b8e56.png
    quiz_text = (
        f"{t('quiz_q', lang)}\n\n"
        f"🇯🇵  **{correct_word['word']}** ({correct_word['romaji']})"
    )

    await send(
        text=quiz_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    # maxsplit=2 so a word containing '_' can't break the unpack.
    lang = get_user_lang(user_id, getattr(query.from_user, "language_code", None))

    parts = query.data.split('_', 2)
    if len(parts) != 3:
        await query.answer(t("quiz_unparsed", lang), show_alert=True)
        return
    _, result, correct_word_key = parts

    words = load_words()
    word_info = next((w for w in words if w['word'] == correct_word_key), None)

    if word_info is None:
        # The word was renamed or removed since this message was sent —
        # e.g. pressing a button on an old message after a DB change.
        await query.message.edit_text(
            t("quiz_stale", lang),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t("btn_new_q", lang), callback_data='quiz_start')],
                [InlineKeyboardButton(t("btn_menu", lang), callback_data='menu_main')]
            ])
        )
        return

    if result == "correct":
        xp, streak = save_score_and_streak(user_id, 10)
        feedback = t("quiz_right", lang, streak=streak, xp=xp)
    else:
        stats = get_user_stats(user_id)
        xp = stats['xp'] if isinstance(stats, sqlite3.Row) else 0
        answer = word_info['ru_meaning'] if lang == 'ru' else word_info['en_meaning']
        feedback = t("quiz_wrong", lang, xp=xp, answer=answer)

    next_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_next_q", lang), callback_data='quiz_start')],
        [InlineKeyboardButton(t("btn_menu", lang), callback_data='menu_main')]
    ])

    # A text message can't be edited into a voice message, so to keep the
    # answer in a single bubble we replace it: delete the question, then send
    # the result with the audio attached.
    #
    # The delete and the send are tracked separately on purpose. An earlier
    # version wrapped both in one try and fell back to edit_text — but if the
    # delete had already succeeded, that edit targeted a message that no
    # longer existed and raised, surfacing as "something went wrong".
    deleted = False
    try:
        await query.message.delete()
        deleted = True
    except Exception as e:
        logging.info(f"Couldn't delete the quiz question ({e}); leaving it.")

    try:
        await deliver_word(context, query.message.chat_id, word_info,
                           next_keyboard, prefix=f"{feedback}\n\n", lang=lang)
    except Exception as e:
        logging.error(f"Couldn't deliver the quiz result ({e}); sending plain text.")
        response = f"{feedback}\n\n{format_word_message(word_info, lang)}"
        if deleted:
            await context.bot.send_message(chat_id=query.message.chat_id, text=response,
                                           reply_markup=next_keyboard, parse_mode='Markdown')
        else:
            await query.message.edit_text(response, reply_markup=next_keyboard,
                                          parse_mode='Markdown')


# --- ERROR HANDLER ---

async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Catches anything a handler raises.

    Without this, python-telegram-bot logs 'No error handlers are registered'
    and silently discards the update — the user gets no reply at all and the
    bot looks frozen.
    """
    err = context.error

    # Double-tapping a menu button makes Telegram reject the identical edit.
    # It's harmless and needs no user-facing message.
    if isinstance(err, BadRequest) and "not modified" in str(err).lower():
        return

    logging.error("Unhandled error while processing update", exc_info=err)

    if isinstance(update, Update) and update.effective_chat:
        # Look up the language defensively. This handler runs *because*
        # something already failed — quite possibly the database — so a
        # failed lookup must not stop the user being told anything at all.
        lang = "ru"
        try:
            if update.effective_user:
                lang = get_user_lang(update.effective_user.id)
        except Exception:
            logging.warning("Couldn't read user language in error handler")

        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=t("generic_err", lang)
            )
        except Exception:
            # Never let the error handler itself raise.
            logging.exception("Failed to deliver the error notice")


# --- DAILY JOB ---

def pick_unseen_word(user_id, level):
    """Picks a word this user hasn't received as a daily word yet.

    Plain random.choice draws WITH replacement, so it re-sends words the user
    has already seen — with ~460 words there's a ~61% chance of a repeat
    within a month. This walks through the whole level before repeating
    anything ("shuffle bag"), which is also just better for learning.
    """
    words = load_words(level)
    if not words:
        words = load_words()  # level empty (or unset) — fall back to everything
    if not words:
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM sent_words WHERE user_id = ?", (user_id,))
    already_sent = {row["word"] for row in cursor.fetchall()}

    unseen = [w for w in words if w["word"] not in already_sent]

    if not unseen:
        # Every word at this level has been sent — start a new cycle. Hold the
        # most recent word out of the fresh pool, otherwise the cycle boundary
        # can hand out the same word two days running.
        cursor.execute(
            "SELECT word FROM sent_words WHERE user_id = ? ORDER BY rowid DESC LIMIT 1",
            (user_id,)
        )
        last_row = cursor.fetchone()
        last_word = last_row["word"] if last_row else None

        cursor.execute("DELETE FROM sent_words WHERE user_id = ?", (user_id,))
        conn.commit()
        unseen = [w for w in words if w["word"] != last_word] or words
        logging.info(f"User {user_id} completed a full pass of level {level}; cycling.")

    chosen = random.choice(unseen)

    cursor.execute(
        "INSERT OR REPLACE INTO sent_words (user_id, word, sent_at) VALUES (?, ?, ?)",
        (user_id, chosen["word"], datetime.date.today().isoformat())
    )
    conn.commit()
    conn.close()
    return chosen


async def send_daily_word(context: ContextTypes.DEFAULT_TYPE):
    subscribers = load_subscribers()
    for chat_id in subscribers:
        try:
            # Respect each subscriber's own N5/N4 setting — the old code sent
            # from the whole table, so an N5 learner could get N4 words.
            level = get_user_level(chat_id)
            word = pick_unseen_word(chat_id, level)
            if word is None:
                logging.warning("Daily word skipped: word table is empty")
                continue
            sub_lang = get_user_lang(chat_id)
            await deliver_word(context, chat_id, word, get_keyboard(sub_lang),
                               prefix=f"{t('daily_header', sub_lang)}\n\n",
                               lang=sub_lang)
        except Forbidden:
            # User blocked the bot — stop trying to reach them every morning.
            logging.info(f"{chat_id} blocked the bot; unsubscribing them.")
            subs = load_subscribers()
            subs.discard(chat_id)
            save_subscribers(subs)
        except Exception as e:
            logging.error(f"Daily word failed for {chat_id}: {e}")


if __name__ == '__main__':
    init_db()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('info', info_command))
    application.add_handler(CommandHandler('quiz', start_quiz))
    application.add_handler(CommandHandler('settings', settings_menu))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_error_handler(on_error)

    target_time = datetime.time(hour=9, minute=0, second=0, tzinfo=ZoneInfo("Asia/Tashkent"))
    application.job_queue.run_daily(send_daily_word, time=target_time)

    print("Bot is running with DB, XP and Streaks...")
    application.run_polling()
