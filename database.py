"""
database.py — sirf DB se related kaam yahan hota hai.
UPDATED: ab 'users' table add hui hai, aur baaki har table mein
user_id column hai taake data users ke beech separate rahe.
"""

import sqlite3
from config import DB_PATH


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    c = conn.cursor()

    # NAYA: users table — login credentials yahan store hoti hain.
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")

    # CHANGED: profile ab har user ke liye alag row rakhta hai (id=1 hardcode hata diya).
    c.execute("""CREATE TABLE IF NOT EXISTS profile (
        user_id INTEGER PRIMARY KEY,
        name TEXT, age INTEGER, gender TEXT,
        height_cm REAL, weight_kg REAL,
        goal TEXT, activity_level TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    # CHANGED: har log table mein user_id column add hua hai.
    c.execute("""CREATE TABLE IF NOT EXISTS workout_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, date TEXT, exercise TEXT, sets INTEGER, reps INTEGER, weight_kg REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS meal_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, date TEXT, food TEXT, calories REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS weight_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, date TEXT, weight_kg REAL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER, time TEXT, message TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""")

    conn.commit()
    conn.close()
