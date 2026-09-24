from datetime import UTC, datetime

from app.models import Reminder, User
from app.security import hash_password
from app.worker import fire_due_reminders
from tests.conftest import register

# 14:00 UTC is 19:00 in Asia/Karachi (UTC+5)
AT_1900_PKT = datetime(2026, 9, 24, 14, 0, tzinfo=UTC)
AT_1905_PKT = datetime(2026, 9, 24, 14, 5, tzinfo=UTC)
NEXT_DAY_1900_PKT = datetime(2026, 9, 25, 14, 0, tzinfo=UTC)


def add_reminder(db, tz="Asia/Karachi", hhmm="19:00"):
    user = User(username=f"u{tz.replace('/', '')}", password_hash=hash_password("password123"), timezone=tz)
    db.add(user)
    db.commit()
    db.add(Reminder(user_id=user.id, time_hhmm=hhmm, message="Walk time"))
    db.commit()
    return user


def test_fires_once_per_day_in_user_timezone(db):
    add_reminder(db)
    assert fire_due_reminders(db, AT_1900_PKT) == 1
    assert fire_due_reminders(db, AT_1905_PKT) == 0  # already fired today
    assert fire_due_reminders(db, NEXT_DAY_1900_PKT) == 1


def test_does_not_fire_at_same_clock_time_in_other_timezone(db):
    add_reminder(db, tz="Europe/London")  # 14:00 UTC is 15:00 in London
    assert fire_due_reminders(db, AT_1900_PKT) == 0


def test_notification_reaches_the_user_and_can_be_dismissed(client, db):
    headers = register(client, "rema")
    user = db.query(User).filter_by(username="rema").one()
    db.add(Reminder(user_id=user.id, time_hhmm="19:00", message="Paani piyo"))
    db.commit()
    fire_due_reminders(db, AT_1900_PKT)

    notes = client.get("/notifications", headers=headers).json()
    assert [n["message"] for n in notes] == ["Paani piyo"]
    assert client.post(f"/notifications/{notes[0]['id']}/read", headers=headers).status_code == 204
    assert client.get("/notifications", headers=headers).json() == []


def test_cannot_dismiss_someone_elses_notification(client, db):
    owner = register(client, "owner")
    other = register(client, "other")
    user = db.query(User).filter_by(username="owner").one()
    db.add(Reminder(user_id=user.id, time_hhmm="19:00", message="x"))
    db.commit()
    fire_due_reminders(db, AT_1900_PKT)
    note_id = client.get("/notifications", headers=owner).json()[0]["id"]
    assert client.post(f"/notifications/{note_id}/read", headers=other).status_code == 404


def test_postgres_urls_get_the_psycopg_driver():
    from app.config import Settings

    s = Settings(database_url="postgres://u:p@host/db?sslmode=require")
    assert s.database_url == "postgresql+psycopg://u:p@host/db?sslmode=require"
    assert Settings(database_url="sqlite:///./x.db").database_url == "sqlite:///./x.db"


def test_background_worker_starts_and_stops():
    import time

    from app.worker import start_in_background

    stop = start_in_background()
    time.sleep(0.2)
    stop.set()