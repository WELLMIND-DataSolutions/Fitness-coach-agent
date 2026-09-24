"""Reminder worker: turns due reminders into in-app notifications.

Runs either as its own process (`python -m app.worker`) or, on single-service hosting,
as a background thread inside the API (RUN_REMINDER_WORKER_IN_API=true). Each reminder
is claimed with a conditional UPDATE, so even several copies fire it at most once per day.
"""

import logging
import signal
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.logging_setup import configure_logging
from app.models import Notification, Reminder, User

log = logging.getLogger("fitcoach.worker")

# If the worker was down briefly, still deliver reminders due within this window.
GRACE_MINUTES = 15


def _minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def fire_due_reminders(db: Session, now_utc: datetime | None = None) -> int:
    now_utc = now_utc or datetime.now(UTC)
    rows = db.execute(
        select(Reminder.id, Reminder.time_hhmm, Reminder.message, Reminder.user_id, User.timezone)
        .join(User, User.id == Reminder.user_id)
        .where(Reminder.active.is_(True))
    ).all()

    fired = 0
    for reminder_id, time_hhmm, message, user_id, tz in rows:
        local = now_utc.astimezone(ZoneInfo(tz))
        late_by = _minutes(local.strftime("%H:%M")) - _minutes(time_hhmm)
        if not 0 <= late_by <= GRACE_MINUTES:
            continue
        today = local.date()
        claimed = db.execute(
            update(Reminder)
            .where(
                Reminder.id == reminder_id,
                Reminder.active.is_(True),
                or_(Reminder.last_fired_on.is_(None), Reminder.last_fired_on != today),
            )
            .values(last_fired_on=today)
        ).rowcount
        if claimed:
            db.add(Notification(user_id=user_id, message=message))
            fired += 1
        db.commit()
    return fired


def run_loop(should_stop: Callable[[], bool]) -> None:
    """Poll for due reminders until should_stop() returns True."""
    settings = get_settings()
    log.info("Reminder worker started (poll every %ss)", settings.reminder_poll_seconds)
    while not should_stop():
        try:
            with SessionLocal() as db:
                count = fire_due_reminders(db)
            if count:
                log.info("Fired %d reminder(s)", count)
        except Exception:
            log.exception("Reminder pass failed; retrying next cycle")
        for _ in range(settings.reminder_poll_seconds):
            if should_stop():
                break
            time.sleep(1)
    log.info("Reminder worker stopped")


def start_in_background() -> threading.Event:
    """Run the loop in a daemon thread inside the API process. Set the returned event to stop it."""
    stop = threading.Event()
    threading.Thread(target=run_loop, args=(stop.is_set,), name="reminder-worker", daemon=True).start()
    return stop


def main() -> None:
    configure_logging()
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    run_loop(stop.is_set)


if __name__ == "__main__":
    main()