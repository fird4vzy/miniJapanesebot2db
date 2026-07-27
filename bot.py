import datetime
import json
import logging
import os
import random
import sqlite3  # Added SQLite

from zoneinfo import ZoneInfo
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
    conn.commit()
    conn.close()


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

def format_word_message(word_data):
    level = word_data.get('level', 'N5')
    example = word_data.get("example", {})
    msg = (
        f"🏷 **Level:** {level}\n"
        f"🇯🇵 **Word:** {word_data['word']}\n"
        f"📖 **Romaji:** {word_data['romaji']}\n"
        f"🇬🇧 **English:** {word_data['en_meaning']}\n"
        f"🇷🇺 **Russian:** {word_data['ru_meaning']}\n\n"
        f"📝 **Example:**\n"
        f"🇯🇵: {example.get('jp', '-')}\n"
        f"📖: {example.get('romaji', '-')}\n"
        f"🇬🇧: {example.get('en', '-')}\n"
        f"🇷🇺: {example.get('ru', '-')}"
    )
    return msg


def get_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎲 Get Random Word", callback_data='random')],
        [InlineKeyboardButton("🧠 Take a Quiz", callback_data='quiz_start')],
        [InlineKeyboardButton("⚙️ Settings / Level", callback_data='settings_menu')],
        [InlineKeyboardButton("🔔 Subscribe (9 AM)", callback_data='subscribe')],
        [InlineKeyboardButton("🔕 Unsubscribe", callback_data='unsubscribe')]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- SETTINGS MENU ---

async def settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    current_level = get_user_level(user_id)
    text = (
        f"⚙️ **Settings**\n\n"
        f"Current Level: **{current_level}**\n"
        "Choose your difficulty level:"
    )
    keyboard = [
        [
            InlineKeyboardButton(f"{'✅ ' if current_level == 'N5' else ''}N5 (Beginner)", callback_data='set_N5'),
            InlineKeyboardButton(f"{'✅ ' if current_level == 'N4' else ''}N4 (Elementary)", callback_data='set_N4')
        ],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data='menu_main')]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')


# --- HANDLERS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    stats = get_user_stats(user_id)
    xp = stats['xp'] if isinstance(stats, sqlite3.Row) else 0
    streak = stats['streak'] if isinstance(stats, sqlite3.Row) else 0

    text = (
        f"Kon'nichiwa, {user.first_name}! 🇯🇵\n\n"
        f"🔥 **Streak:** {streak} days\n"
        f"🎮 **XP:** {xp} points\n\n"
        "What would you like to do today?"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=get_keyboard(), parse_mode='Markdown')
    else:
        await update.callback_query.message.edit_text(text, reply_markup=get_keyboard(), parse_mode='Markdown')


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_level = get_user_level(user_id)

    if query.data == 'random':
        words = load_words(user_level)  # Uses level preference
        random_word = random.choice(words)
        msg = format_word_message(random_word)
        await query.message.reply_text(msg, parse_mode='Markdown', reply_markup=get_keyboard())

    elif query.data == 'quiz_start':
        await start_quiz(update, context)

    elif query.data.startswith('quiz_'):
        await handle_quiz_answer(update, context)

    elif query.data == 'settings_menu':
        await settings_menu(update, context)

    elif query.data in ['set_N5', 'set_N4']:
        new_level = query.data.split('_')[1]
        save_user_setting(user_id, new_level)
        await settings_menu(update, context)

    elif query.data == 'subscribe':
        subscribers = load_subscribers()
        if user_id not in subscribers:
            subscribers.add(user_id)
            save_subscribers(subscribers)
            await query.message.reply_text("✅ You have subscribed to daily words at 9:00 AM!")
        else:
            await query.message.reply_text("ℹ️ You are already subscribed.")

    elif query.data == 'unsubscribe':
        subscribers = load_subscribers()
        if user_id in subscribers:
            subscribers.remove(user_id)
            save_subscribers(subscribers)
            await query.message.reply_text("❌ You have unsubscribed from daily words.")
        else:
            await query.message.reply_text("ℹ️ You were not subscribed.")

    elif query.data == 'menu_main':
        await start(update, context)


# --- QUIZ ---

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user_level = get_user_level(user_id)

    # Fetch words from DB based on level
    filtered_words = load_words(user_level)
    if not filtered_words:
        filtered_words = load_words()  # fallback to all if level list is empty

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
        # The button displays the English meaning
        keyboard.append(
            [InlineKeyboardButton(opt['en_meaning'], callback_data=f"quiz_{is_right}_{correct_word['word']}")])

    # --- FORMATTED TEXT TO MATCH YOUR IMAGE ---
    # This uses the exact emojis and layout from image_1b8e56.png
    quiz_text = (
        f"❓ **How do you translate this?**\n\n"
        f"🇯🇵  **{correct_word['word']}** ({correct_word['romaji']})"
    )

    await query.message.edit_text(
        text=quiz_text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    _, result, correct_word_key = query.data.split('_')

    words = load_words()
    word_info = next((w for w in words if w['word'] == correct_word_key), None)

    if result == "correct":
        xp, streak = save_score_and_streak(user_id, 10)
        feedback = f"✅ **Correct! (+10 XP)**\n🔥 Streak: {streak} days | 🎮 Total XP: {xp}"
    else:
        stats = get_user_stats(user_id)
        xp = stats['xp'] if isinstance(stats, sqlite3.Row) else 0
        feedback = f"❌ **Wrong!**\n🎮 Total XP: {xp}\n\nThe correct answer was **{word_info['en_meaning']}**."

    response = f"{feedback}\n\n{format_word_message(word_info)}"
    next_keyboard = [[InlineKeyboardButton("🔄 Next Question", callback_data='quiz_start')],
                     [InlineKeyboardButton("🏁 Menu", callback_data='menu_main')]]

    await query.message.edit_text(response, reply_markup=InlineKeyboardMarkup(next_keyboard), parse_mode='Markdown')


# --- DAILY JOB ---

async def send_daily_word(context: ContextTypes.DEFAULT_TYPE):
    words = load_words()
    subscribers = load_subscribers()
    for chat_id in subscribers:
        try:
            word = random.choice(words)
            await context.bot.send_message(chat_id=chat_id, text=f"☀️ **Daily Word!**\n\n{format_word_message(word)}",
                                           parse_mode='Markdown', reply_markup=get_keyboard())
        except Exception as e:
            logging.error(f"Error: {e}")


if __name__ == '__main__':
    init_db()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))

    target_time = datetime.time(hour=9, minute=0, second=0, tzinfo=ZoneInfo("Asia/Tashkent"))
    application.job_queue.run_daily(send_daily_word, time=target_time)

    print("Bot is running with DB, XP and Streaks...")
    application.run_polling()
