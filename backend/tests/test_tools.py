import pytest
from sqlalchemy import select

from app.models import User
from app.security import hash_password
from app.tools import (
    ToolContext,
    ToolError,
    calculate_calories,
    delete_reminder,
    generate_workout_plan,
    get_progress_summary,
    list_reminders,
    log_meal,
    log_weight,
    log_workout,
    set_profile,
    set_reminder,
)


def make_user(db, name="u1"):
    user = User(username=name, password_hash=hash_password("password123"), timezone="Asia/Karachi")
    db.add(user)
    db.commit()
    return ToolContext(db=db, user=user)


PROFILE = dict(
    name="Ali", age=30, gender="male", height_cm=175, weight_kg=80, goal="weight_loss", activity_level="moderate"
)


def test_calories_follow_mifflin_st_jeor(db):
    ctx = make_user(db)
    set_profile(ctx, **PROFILE)
    result = calculate_calories(ctx)
    # BMR = 10*80 + 6.25*175 - 5*30 + 5 = 1748.75 ; TDEE = 1748.75*1.55
    assert result["bmr"] == 1749
    assert result["tdee"] == round(1748.75 * 1.55)
    assert result["target_calories"] == round(1748.75 * 1.55 - 500)


def test_calorie_target_never_goes_below_floor(db):
    ctx = make_user(db)
    set_profile(
        ctx,
        **{**PROFILE, "gender": "female", "weight_kg": 45, "height_cm": 150, "age": 60, "activity_level": "sedentary"},
    )
    result = calculate_calories(ctx)
    assert result["target_calories"] == 1200
    assert result["floor_applied"] is True


def test_profile_validation(db):
    ctx = make_user(db)
    with pytest.raises(ToolError):
        set_profile(ctx, **{**PROFILE, "age": 7})
    with pytest.raises(ToolError):
        set_profile(ctx, **{**PROFILE, "activity_level": "couch"})
    assert set_profile(ctx, **{**PROFILE, "goal": "Muscle Gain"})["goal"] == "muscle_gain"


def test_calories_without_profile_asks_for_profile(db):
    with pytest.raises(ToolError, match="No profile"):
        calculate_calories(make_user(db))


def test_workout_plan_supports_up_to_six_days(db):
    ctx = make_user(db)
    assert len(generate_workout_plan(ctx, goal="muscle_gain", days_per_week=6)["plan"]) == 6
    with pytest.raises(ToolError):
        generate_workout_plan(ctx, goal="muscle_gain", days_per_week=7)


def test_logs_and_progress_are_isolated_per_user(db):
    a, b = make_user(db, "a"), make_user(db, "b")
    log_workout(a, "Squats", 3, 10, 60)
    log_meal(a, "Daal chawal", 650)
    log_meal(a, "Chai", 120)
    log_weight(a, 80.5)
    log_meal(b, "Pizza", 900)

    summary = get_progress_summary(a)
    assert summary["workouts_last_7_days"] == 1
    assert summary["calories_last_7_days"][0]["total_calories"] == 770
    assert summary["weight_history"][0]["weight_kg"] == 80.5
    assert get_progress_summary(b)["workouts_last_7_days"] == 0


def test_log_validation(db):
    ctx = make_user(db)
    with pytest.raises(ToolError):
        log_workout(ctx, "", 3, 10)
    with pytest.raises(ToolError):
        log_meal(ctx, "Cake", -5)
    with pytest.raises(ToolError):
        log_weight(ctx, "heavy")


def test_reminders_validate_time_and_are_scoped_to_user(db):
    a, b = make_user(db, "a"), make_user(db, "b")
    with pytest.raises(ToolError):
        set_reminder(a, "7pm", "Walk")
    rid = set_reminder(a, "19:00", "Walk")["id"]
    assert list_reminders(a)["reminders"][0]["time"] == "19:00"
    with pytest.raises(ToolError):
        delete_reminder(b, rid)  # b cannot delete a's reminder
    delete_reminder(a, rid)
    assert list_reminders(a)["reminders"] == []
    assert db.scalar(select(User).where(User.username == "a")) is not None