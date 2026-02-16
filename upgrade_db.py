import sqlite3

# Connect to your existing database
conn = sqlite3.connect('japanese_bot.db')
cursor = conn.cursor()

# Create the USERS table to track XP and Streaks
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    xp INTEGER DEFAULT 0,
    streak INTEGER DEFAULT 0,
    last_active_date TEXT
)
''')

conn.commit()
conn.close()
print("✅ Database successfully upgraded with User Stats!")