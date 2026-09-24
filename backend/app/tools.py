"""Business-logic tools the LLM can call, plus their JSON schemas.

Each tool receives a ToolContext (DB session + the authenticated user). The user
is never an argument the model controls, so one user cannot touch another's data.
Invalid input raises ToolError, which the agent returns to the model as {"error": ...}
so it can ask the user to correct it.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import MealLog, Profile, Reminder, User, WeightLog, WorkoutLog

GENDERS = ("male", "female")
GOALS = ("weight_loss", "muscle_gain", "general_fitness")
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}
MAX_ACTIVE_REMINDERS = 10
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ToolError(Exception):
    """Input the model should ask the user to fix."""


@dataclass
class ToolContext:
    db: Session
    user: User

    def today(self) -> date:
        return datetime.now(ZoneInfo(self.user.timezone)).date()


def _number(value: Any, name: str, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ToolError(f"{name} must be a number") from None
    if not low <= number <= high:
        raise ToolError(f"{name} must be between {low:g} and {high:g}")
    return number


def _text(value: Any, name: str, max_len: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ToolError(f"{name} cannot be empty")
    if len(text) > max_len:
        raise ToolError(f"{name} must be at most {max_len} characters")
    return text


def _choice(value: Any, name: str, options: tuple[str, ...] | list[str]) -> str:
    text = str(value or "").strip().lower().replace(" ", "_")
    if text not in options:
        raise ToolError(f"{name} must be one of: {', '.join(options)}")
    return text


def _load_profile(ctx: ToolContext) -> Profile:
    profile = ctx.db.get(Profile, ctx.user.id)
    if profile is None:
        raise ToolError("No profile saved yet. Ask the user for their details and call set_profile.")
    return profile


# ---------------------------------------------------------------- profile


def set_profile(ctx: ToolContext, name, age, gender, height_cm, weight_kg, goal, activity_level) -> dict:
    values = {
        "name": _text(name, "name", 80),
        "age": int(_number(age, "age", 13, 100)),
        "gender": _choice(gender, "gender", GENDERS),
        "height_cm": _number(height_cm, "height_cm", 100, 250),
        "weight_kg": _number(weight_kg, "weight_kg", 25, 350),
        "goal": _choice(goal, "goal", GOALS),
        "activity_level": _choice(activity_level, "activity_level", list(ACTIVITY_MULTIPLIERS)),
    }
    profile = ctx.db.get(Profile, ctx.user.id)
    if profile is None:
        profile = Profile(user_id=ctx.user.id, **values)
        ctx.db.add(profile)
    else:
        for key, value in values.items():
            setattr(profile, key, value)
    ctx.db.commit()
    return {"status": "saved", **values}


def get_profile(ctx: ToolContext) -> dict:
    p = _load_profile(ctx)
    return {
        "name": p.name,
        "age": p.age,
        "gender": p.gender,
        "height_cm": p.height_cm,
        "weight_kg": p.weight_kg,
        "goal": p.goal,
        "activity_level": p.activity_level,
    }


# ---------------------------------------------------------------- calculations


def calculate_calories(ctx: ToolContext) -> dict:
    p = _load_profile(ctx)
    # Mifflin-St Jeor
    bmr = 10 * p.weight_kg + 6.25 * p.height_cm - 5 * p.age + (5 if p.gender == "male" else -161)
    tdee = bmr * ACTIVITY_MULTIPLIERS[p.activity_level]
    adjustment = {"weight_loss": -500, "muscle_gain": 300}.get(p.goal, 0)
    # Never recommend going below a conservative floor without professional supervision.
    floor = 1500 if p.gender == "male" else 1200
    target = max(tdee + adjustment, floor)

    protein_g = p.weight_kg * (2.0 if p.goal == "muscle_gain" else 1.6)
    fat_g = target * 0.25 / 9
    carb_g = max((target - protein_g * 4 - fat_g * 9) / 4, 0)

    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "target_calories": round(target),
        "floor_applied": target == floor,
        "macros": {"protein_g": round(protein_g), "fat_g": round(fat_g), "carbs_g": round(carb_g)},
        "note": "Estimates from the Mifflin-St Jeor formula, not a medical measurement.",
    }


WORKOUT_TEMPLATES: dict[str, list[tuple[str, list[str]]]] = {
    "weight_loss": [
        ("Full body + cardio", ["Squats 3x12", "Push-ups 3x15", "Bent-over rows 3x12", "Plank 3x30s", "20 min cardio"]),
        ("HIIT", ["Jump squats", "Burpees", "Mountain climbers", "20 min HIIT circuit"]),
        ("Upper body", ["Bench press 3x10", "Lat pulldown 3x12", "Shoulder press 3x10", "Bicep curls 3x12"]),
        ("Lower body + core", ["Lunges 3x12", "Deadlifts 3x10", "Leg press 3x12", "Ab circuit 3 rounds"]),
        ("Steady cardio", ["40 min brisk walk, cycle or swim"]),
        ("Full body circuit", ["Kettlebell swings 3x15", "Goblet squats 3x12", "Push-ups 3x12", "Rows 3x12"]),
    ],
    "muscle_gain": [
        ("Chest + triceps", ["Bench press 4x8", "Incline DB press 3x10", "Dips 3x10", "Tricep pushdown 3x12"]),
        ("Back + biceps", ["Deadlift 4x6", "Pull-ups 3x8", "Barbell row 3x10", "Bicep curl 3x12"]),
        ("Legs", ["Squats 4x8", "Leg press 3x12", "Romanian deadlift 3x10", "Calf raises 4x15"]),
        ("Shoulders + abs", ["Overhead press 4x8", "Lateral raises 3x15", "Face pulls 3x15", "Ab circuit"]),
        ("Upper body volume", ["Incline bench 3x10", "Cable rows 3x12", "Arnold press 3x10", "Hammer curls 3x12"]),
        ("Lower body volume", ["Front squats 3x10", "Hip thrusts 3x12", "Leg curls 3x12", "Walking lunges 3x12"]),
    ],
    "general_fitness": [
        ("Full body", ["Squats 3x12", "Push-ups 3x12", "Rows 3x12", "Plank 3x30s"]),
        ("Cardio + core", ["30 min brisk walk or jog", "Ab circuit 3 rounds"]),
        ("Full body", ["Lunges 3x12", "Bench press 3x10", "Lat pulldown 3x12"]),
        ("Active recovery", ["Yoga or stretching", "Light walk 20 min"]),
        ("Mixed conditioning", ["Rowing 15 min", "Step-ups 3x12", "Farmer carries 3x40m"]),
        ("Mobility", ["Hip and shoulder mobility 20 min", "Light walk 20 min"]),
    ],
}


def generate_workout_plan(ctx: ToolContext, goal=None, days_per_week=4) -> dict:
    if goal is None:
        profile = ctx.db.get(Profile, ctx.user.id)
        goal = profile.goal if profile else "general_fitness"
    goal = _choice(goal, "goal", GOALS)
    days = int(_number(days_per_week if days_per_week is not None else 4, "days_per_week", 1, 6))
    plan = WORKOUT_TEMPLATES[goal][:days]
    return {
        "goal": goal,
        "days_per_week": days,
        "plan": [{"day": f"Day {i} - {title}", "exercises": ex} for i, (title, ex) in enumerate(plan, start=1)],
    }


# ---------------------------------------------------------------- logging


def log_workout(ctx: ToolContext, exercise, sets, reps, weight_kg=0) -> dict:
    row = WorkoutLog(
        user_id=ctx.user.id,
        logged_on=ctx.today(),
        exercise=_text(exercise, "exercise", 100),
        sets=int(_number(sets, "sets", 1, 50)),
        reps=int(_number(reps, "reps", 1, 200)),
        weight_kg=_number(weight_kg or 0, "weight_kg", 0, 500),
    )
    ctx.db.add(row)
    ctx.db.commit()
    return {"status": "logged", "exercise": row.exercise, "date": str(row.logged_on)}


def log_meal(ctx: ToolContext, food, calories) -> dict:
    row = MealLog(
        user_id=ctx.user.id,
        logged_on=ctx.today(),
        food=_text(food, "food", 200),
        calories=_number(calories, "calories", 0, 5000),
    )
    ctx.db.add(row)
    ctx.db.commit()
    return {"status": "logged", "food": row.food, "calories": row.calories, "date": str(row.logged_on)}


def log_weight(ctx: ToolContext, weight_kg) -> dict:
    row = WeightLog(user_id=ctx.user.id, logged_on=ctx.today(), weight_kg=_number(weight_kg, "weight_kg", 25, 350))
    ctx.db.add(row)
    ctx.db.commit()
    return {"status": "logged", "weight_kg": row.weight_kg, "date": str(row.logged_on)}


def get_progress_summary(ctx: ToolContext) -> dict:
    uid = ctx.user.id
    since = ctx.today() - timedelta(days=6)

    weights = ctx.db.execute(
        select(WeightLog.logged_on, WeightLog.weight_kg)
        .where(WeightLog.user_id == uid)
        .order_by(WeightLog.logged_on.desc(), WeightLog.id.desc())
        .limit(30)
    ).all()
    calories = ctx.db.execute(
        select(MealLog.logged_on, func.sum(MealLog.calories))
        .where(MealLog.user_id == uid, MealLog.logged_on >= since)
        .group_by(MealLog.logged_on)
        .order_by(MealLog.logged_on)
    ).all()
    workouts = ctx.db.scalar(
        select(func.count()).select_from(WorkoutLog).where(WorkoutLog.user_id == uid, WorkoutLog.logged_on >= since)
    )

    return {
        "weight_history": [{"date": str(d), "weight_kg": w} for d, w in reversed(weights)],
        "calories_last_7_days": [{"date": str(d), "total_calories": round(c)} for d, c in calories],
        "workouts_last_7_days": workouts or 0,
    }


# ---------------------------------------------------------------- reminders


def set_reminder(ctx: ToolContext, time_hhmm, message) -> dict:
    time_hhmm = str(time_hhmm or "").strip()
    if not TIME_RE.match(time_hhmm):
        raise ToolError("time_hhmm must be 24-hour HH:MM, e.g. 07:30 or 19:00")
    active = ctx.db.scalar(
        select(func.count()).select_from(Reminder).where(Reminder.user_id == ctx.user.id, Reminder.active.is_(True))
    )
    if active >= MAX_ACTIVE_REMINDERS:
        raise ToolError(f"The user already has {MAX_ACTIVE_REMINDERS} reminders; delete one first")
    now_local = datetime.now(ZoneInfo(ctx.user.timezone))
    # If the time already passed today, start from tomorrow instead of firing immediately.
    already_passed = time_hhmm <= now_local.strftime("%H:%M")
    reminder = Reminder(
        user_id=ctx.user.id,
        time_hhmm=time_hhmm,
        message=_text(message, "message", 200),
        last_fired_on=now_local.date() if already_passed else None,
    )
    ctx.db.add(reminder)
    ctx.db.commit()
    return {"status": "reminder_set", "id": reminder.id, "time": time_hhmm, "timezone": ctx.user.timezone}


def list_reminders(ctx: ToolContext) -> dict:
    rows = ctx.db.scalars(
        select(Reminder).where(Reminder.user_id == ctx.user.id, Reminder.active.is_(True)).order_by(Reminder.time_hhmm)
    ).all()
    return {"reminders": [{"id": r.id, "time": r.time_hhmm, "message": r.message} for r in rows]}


def delete_reminder(ctx: ToolContext, reminder_id) -> dict:
    reminder = ctx.db.get(Reminder, int(_number(reminder_id, "reminder_id", 1, 2**31)))
    if reminder is None or reminder.user_id != ctx.user.id or not reminder.active:
        raise ToolError("No active reminder with that id")
    reminder.active = False
    ctx.db.commit()
    return {"status": "deleted", "id": reminder.id}


# ---------------------------------------------------------------- registry

NO_PARAMS = {"type": "object", "properties": {}}


@dataclass(frozen=True)
class Tool:
    fn: Callable[..., dict]
    description: str
    parameters: dict


TOOLS: dict[str, Tool] = {
    "set_profile": Tool(
        set_profile,
        "Save or replace the user's fitness profile. Call when the user gives their details or wants to update them.",
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "description": "Years"},
                "gender": {"type": "string", "enum": list(GENDERS)},
                "height_cm": {"type": "number"},
                "weight_kg": {"type": "number"},
                "goal": {"type": "string", "enum": list(GOALS)},
                "activity_level": {"type": "string", "enum": list(ACTIVITY_MULTIPLIERS)},
            },
            "required": ["name", "age", "gender", "height_cm", "weight_kg", "goal", "activity_level"],
        },
    ),
    "get_profile": Tool(get_profile, "Fetch the user's saved profile.", NO_PARAMS),
    "calculate_calories": Tool(
        calculate_calories,
        "Calculate BMR, TDEE, daily calorie target and macros from the saved profile. "
        "Always use this for calorie or macro questions; never calculate them yourself.",
        NO_PARAMS,
    ),
    "generate_workout_plan": Tool(
        generate_workout_plan,
        "Generate a weekly workout plan. Always use this instead of inventing exercises.",
        {
            "type": "object",
            "properties": {
                "goal": {"type": "string", "enum": list(GOALS), "description": "Defaults to the profile goal"},
                "days_per_week": {"type": "integer", "minimum": 1, "maximum": 6},
            },
        },
    ),
    "log_workout": Tool(
        log_workout,
        "Log one completed exercise for today.",
        {
            "type": "object",
            "properties": {
                "exercise": {"type": "string"},
                "sets": {"type": "integer"},
                "reps": {"type": "integer"},
                "weight_kg": {"type": "number", "description": "0 for bodyweight exercises"},
            },
            "required": ["exercise", "sets", "reps"],
        },
    ),
    "log_meal": Tool(
        log_meal,
        "Log a meal eaten today with its calories.",
        {
            "type": "object",
            "properties": {"food": {"type": "string"}, "calories": {"type": "number"}},
            "required": ["food", "calories"],
        },
    ),
    "log_weight": Tool(
        log_weight,
        "Log the user's body weight for today.",
        {"type": "object", "properties": {"weight_kg": {"type": "number"}}, "required": ["weight_kg"]},
    ),
    "get_progress_summary": Tool(
        get_progress_summary,
        "Summarise weight history, calories for the last 7 days and workouts in the last 7 days.",
        NO_PARAMS,
    ),
    "set_reminder": Tool(
        set_reminder,
        "Create a daily reminder shown in the app at a local time. Convert phrases like "
        "'7 in the evening' to 24-hour HH:MM before calling.",
        {
            "type": "object",
            "properties": {
                "time_hhmm": {"type": "string", "description": "24-hour local time, e.g. 19:00"},
                "message": {"type": "string"},
            },
            "required": ["time_hhmm", "message"],
        },
    ),
    "list_reminders": Tool(list_reminders, "List the user's active daily reminders.", NO_PARAMS),
    "delete_reminder": Tool(
        delete_reminder,
        "Delete one of the user's reminders by id (get ids from list_reminders).",
        {"type": "object", "properties": {"reminder_id": {"type": "integer"}}, "required": ["reminder_id"]},
    ),
}


def openai_tool_specs() -> list[dict]:
    return [
        {"type": "function", "function": {"name": name, "description": t.description, "parameters": t.parameters}}
        for name, t in TOOLS.items()
    ]