"""
reminder_scheduler.py — background thread jo har minute reminders table check karta hai
aur jab time match ho jaye, terminal pe alert print karta hai.

Note: 'time_str' format expect karta hai jaisa user ne diya ho, e.g. '19:00' ya '07:00'.
Agar user ne natural language di ho (jaise "shaam 7 baje"), LLM ko system_prompt mein
guide karo ke wo ise 24-hour 'HH:MM' format mein convert kar ke hi set_reminder ko bheje.
"""

import threading
import time as time_module
from datetime import datetime
from database import get_connection


def check_reminders_loop(interval_seconds=60):
    """Har 'interval_seconds' baad reminders check karta hai, matching time pe alert deta hai."""
    already_fired_today = set()

    while True:
        now = datetime.now()
        current_time_str = now.strftime("%H:%M")
        today = now.strftime("%Y-%m-%d")

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT id, time, message FROM reminders")
        rows = c.fetchall()
        conn.close()

        for reminder_id, time_str, message in rows:
            key = f"{reminder_id}-{today}"
            if time_str.strip() == current_time_str and key not in already_fired_today:
                print(f"\n🔔 REMINDER [{current_time_str}]: {message}\n")
                already_fired_today.add(key)

        time_module.sleep(interval_seconds)


def start_scheduler():
    """Background thread mein scheduler start karta hai — main chat loop block nahi hoga."""
    thread = threading.Thread(target=check_reminders_loop, daemon=True)
    thread.start()