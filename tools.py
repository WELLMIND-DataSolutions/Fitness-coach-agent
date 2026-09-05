"""
tools.py — asli kaam karne wale functions.
Ye functions database.py use karte hain data save/read karne ke liye.
Har function ek "tool" hai jo agent Groq API ke zariye call karega.
"""

from datetime import date
from database import get_connection


def set_profile(name, age, gender, height_cm, weight_kg, goal, activity_level):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM profile")
    c.execute(
        """INSERT INTO profile (id, name, age, gender, height_cm, weight_kg, goal, activity_level)
           VALUES (1, ?, ?, ?, ?, ?, ?, ?)""",
        (name, age, gender, height_cm, weight_kg, goal, activity_level),
    )
    conn.commit()
    conn.close()
    return {"status": "saved", "name": name, "goal": goal}


def get_profile():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT name, age, gender, height_cm, weight_kg, goal, activity_level FROM profile WHERE id=1")
    row = c.fetchone()
    conn.close()
    if not row:
        return {"error": "No profile set yet. Pehle set_profile call karo."}

    keys = ["name", "age", "gender", "height_cm", "weight_kg", "goal", "activity_level"]
    profile = dict(zip(keys, row))

    # FIX 1: partial/corrupt row se aane wale None values ko yahin catch karo,
    # taake baad mein calculate_calories() jaise functions .lower() pe crash na karein.
    required_fields = ["name", "age", "gender", "height_cm", "weight_kg", "goal", "activity_level"]
    missing = [f for f in required_fields if profile.get(f) in (None, "")]
    if missing:
        return {"error": f"Profile incomplete hai, ye fields missing hain: {', '.join(missing)}. Dobara set_profile call karein."}

    return profile


def calculate_calories():
    p = get_profile()
    if "error" in p:
        return p

    if p["gender"].lower() in ("male", "m"):
        bmr = 10 * p["weight_kg"] + 6.25 * p["height_cm"] - 5 * p["age"] + 5
    else:
        bmr = 10 * p["weight_kg"] + 6.25 * p["height_cm"] - 5 * p["age"] - 161

    multipliers = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
    mult = multipliers.get(p["activity_level"].lower(), 1.375)
    tdee = bmr * mult

    goal = p["goal"].lower()
    if "loss" in goal or "cut" in goal:
        target = tdee - 500
    elif "gain" in goal or "muscle" in goal or "bulk" in goal:
        target = tdee + 300
    else:
        target = tdee

    protein_g = p["weight_kg"] * 2
    fat_g = (target * 0.25) / 9
    carb_g = (target - (protein_g * 4 + fat_g * 9)) / 4

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "target_calories": round(target),
        "macros": {"protein_g": round(protein_g), "fat_g": round(fat_g), "carbs_g": round(carb_g)},
    }


def generate_workout_plan(goal=None, days_per_week=4):
    p = get_profile()
    goal = (goal or (p.get("goal") if "error" not in p else "general fitness")).lower()

    templates = {
        "loss": [
            ("Day 1 - Full Body + Cardio", ["Squats 3x12", "Push-ups 3x15", "Bent-over Rows 3x12", "Plank 3x30s", "20 min cardio"]),
            ("Day 2 - HIIT", ["Jump Squats", "Burpees", "Mountain Climbers", "20 min HIIT circuit"]),
            ("Day 3 - Upper Body", ["Bench Press 3x10", "Lat Pulldown 3x12", "Shoulder Press 3x10", "Bicep Curls 3x12"]),
            ("Day 4 - Lower Body + Core", ["Lunges 3x12", "Deadlifts 3x10", "Leg Press 3x12", "Ab Circuit 3 rounds"]),
        ],
        "muscle": [
            ("Day 1 - Chest & Triceps", ["Bench Press 4x8", "Incline DB Press 3x10", "Dips 3x10", "Tricep Pushdown 3x12"]),
            ("Day 2 - Back & Biceps", ["Deadlift 4x6", "Pull-ups 3x8", "Barbell Row 3x10", "Bicep Curl 3x12"]),
            ("Day 3 - Legs", ["Squats 4x8", "Leg Press 3x12", "Romanian Deadlift 3x10", "Calf Raises 4x15"]),
            ("Day 4 - Shoulders & Abs", ["Overhead Press 4x8", "Lateral Raises 3x15", "Face Pulls 3x15", "Ab Circuit"]),
        ],
        "general": [
            ("Day 1 - Full Body", ["Squats 3x12", "Push-ups 3x12", "Rows 3x12", "Plank 3x30s"]),
            ("Day 2 - Cardio + Core", ["30 min brisk walk/jog", "Ab Circuit 3 rounds"]),
            ("Day 3 - Full Body", ["Lunges 3x12", "Bench Press 3x10", "Lat Pulldown 3x12"]),
            ("Day 4 - Active Recovery", ["Yoga / Stretching", "Light walk 20 min"]),
        ],
    }

    key = "loss" if "loss" in goal else "muscle" if ("muscle" in goal or "gain" in goal) else "general"
    base_plan = templates[key]

    # FIX 2: days_per_week ko 1-4 ke range mein clamp karo. Sirf 4 unique day-templates
    # available hain, is se zyada maangne par pehle wale din repeat nahi honge —
    # bas jitne available hain utne hi return honge (silently duplicate karne se better).
    days_per_week = max(1, min(int(days_per_week or 4), len(base_plan)))
    plan = base_plan[:days_per_week]

    return {"goal": goal, "days_per_week": days_per_week, "plan": [{"day": d, "exercises": e} for d, e in plan]}


def log_workout(exercise, sets, reps, weight_kg=0):
    # FIX 3: light input validation — LLM se aane wale tool-call arguments par
    # blindly trust nahi karte. Bounds check karke garbage data DB mein jaane se rokte hain.
    if not exercise or not str(exercise).strip():
        return {"error": "Exercise ka naam khali nahi ho sakta."}
    try:
        sets = int(sets)
        reps = int(reps)
        weight_kg = float(weight_kg)
    except (TypeError, ValueError):
        return {"error": "sets, reps aur weight_kg numeric hone chahiye."}

    if sets <= 0 or sets > 50:
        return {"error": "sets ki value 1-50 ke beech honi chahiye."}
    if reps <= 0 or reps > 200:
        return {"error": "reps ki value 1-200 ke beech honi chahiye."}
    if weight_kg < 0 or weight_kg > 500:
        return {"error": "weight_kg valid range (0-500) mein nahi hai."}

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO workout_log (date, exercise, sets, reps, weight_kg) VALUES (?, ?, ?, ?, ?)",
        (str(date.today()), exercise.strip(), sets, reps, weight_kg),
    )
    conn.commit()
    conn.close()
    return {"status": "logged", "exercise": exercise, "date": str(date.today())}


def log_meal(food, calories):
    # FIX 3 (continued): negative/unrealistic calories reject karo.
    if not food or not str(food).strip():
        return {"error": "Food ka naam khali nahi ho sakta."}
    try:
        calories = float(calories)
    except (TypeError, ValueError):
        return {"error": "calories numeric honi chahiye."}

    if calories < 0 or calories > 10000:
        return {"error": "calories ki value 0-10000 ke beech honi chahiye (ek meal ke liye)."}

    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO meal_log (date, food, calories) VALUES (?, ?, ?)", (str(date.today()), food.strip(), calories))
    conn.commit()
    conn.close()
    return {"status": "logged", "food": food, "calories": calories}


def log_weight(weight_kg):
    # FIX 3 (continued): realistic human weight range check.
    try:
        weight_kg = float(weight_kg)
    except (TypeError, ValueError):
        return {"error": "weight_kg numeric honi chahiye."}

    if weight_kg < 20 or weight_kg > 400:
        return {"error": "weight_kg valid human range (20-400 kg) mein nahi hai."}

    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO weight_log (date, weight_kg) VALUES (?, ?)", (str(date.today()), weight_kg))
    conn.commit()
    conn.close()
    return {"status": "logged", "weight_kg": weight_kg, "date": str(date.today())}


def get_progress_summary():
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT date, weight_kg FROM weight_log ORDER BY date")
    weights = c.fetchall()

    c.execute("SELECT date, SUM(calories) FROM meal_log GROUP BY date ORDER BY date DESC LIMIT 7")
    calories_last7 = c.fetchall()

    c.execute("SELECT COUNT(*) FROM workout_log WHERE date >= date('now', '-7 days')")
    workouts_last7 = c.fetchone()[0]

    conn.close()
    return {
        "weight_history": [{"date": d, "weight_kg": w} for d, w in weights],
        "calories_last_7_days": [{"date": d, "total_calories": cal} for d, cal in calories_last7],
        "workouts_last_7_days": workouts_last7,
    }


def set_reminder(time_str, message):
    if not time_str or not str(time_str).strip():
        return {"error": "time_str khali nahi ho sakta."}
    if not message or not str(message).strip():
        return {"error": "message khali nahi ho sakta."}

    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO reminders (time, message) VALUES (?, ?)", (time_str.strip(), message.strip()))
    conn.commit()
    conn.close()
    return {"status": "reminder_set", "time": time_str, "message": message}