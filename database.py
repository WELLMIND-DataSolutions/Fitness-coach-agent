"""
database.py — sirf DB se related kaam yahan hota hai.
Koi business logic nahi, sirf tables banana aur connection dena.
"""

import sqlite3
from config import DB_PATH


def get_connection():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        name TEXT, age INTEGER, gender TEXT,
        height_cm REAL, weight_kg REAL,
        goal TEXT, activity_level TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS workout_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, exercise TEXT, sets INTEGER, reps INTEGER, weight_kg REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS meal_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, food TEXT, calories REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS weight_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, weight_kg REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        time TEXT, message TEXT
    )""")

    conn.commit()
    conn.close()