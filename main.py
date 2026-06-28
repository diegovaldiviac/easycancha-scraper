import os
import time

import schedule
from dotenv import load_dotenv

from services.auth import login
from services.booking import book, next_target_date
from services.browser import create_browser
from services.logger import logger

load_dotenv()

_TARGET_DAY           = os.getenv("TARGET_DAY",           "Saturday")
_BOOKING_RELEASE_HOUR = os.getenv("BOOKING_RELEASE_HOUR", "00:00")
_BOOKING_ADVANCE_DAYS = int(os.getenv("BOOKING_ADVANCE_DAYS", "7"))

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}

_SCHEDULE = {
    "monday":    schedule.every().monday,
    "tuesday":   schedule.every().tuesday,
    "wednesday": schedule.every().wednesday,
    "thursday":  schedule.every().thursday,
    "friday":    schedule.every().friday,
    "saturday":  schedule.every().saturday,
    "sunday":    schedule.every().sunday,
}


def run() -> None:
    """Entry point called by the scheduler on each trigger."""
    target = next_target_date()
    logger.info(f"Scheduled run — booking {_TARGET_DAY} {target}")
    try:
        with create_browser() as page:
            login(page)
            book(page, target)
    except Exception as e:
        logger.error(f"Run failed: {e}")


def _trigger_day() -> str:
    """
    Compute the weekday on which the scraper should fire.

    easycancha opens its booking window BOOKING_ADVANCE_DAYS before the
    target slot, so we run that many days earlier at BOOKING_RELEASE_HOUR.

    Example with defaults (TARGET_DAY=Saturday, BOOKING_ADVANCE_DAYS=7):
      trigger day = Saturday (same weekday, one week prior)
      equivalent cron: 0 0 * * 6
    """
    target_num  = _WEEKDAYS[_TARGET_DAY.lower()]
    trigger_num = (target_num - _BOOKING_ADVANCE_DAYS) % 7
    return next(name for name, num in _WEEKDAYS.items() if num == trigger_num)


def setup() -> None:
    trigger = _trigger_day()
    _SCHEDULE[trigger].at(_BOOKING_RELEASE_HOUR).do(run)
    logger.info(
        f"Scheduler ready — fires every {trigger.capitalize()} "
        f"at {_BOOKING_RELEASE_HOUR} "
        f"({_BOOKING_ADVANCE_DAYS} days before {_TARGET_DAY} "
        f"slot at {os.getenv('TARGET_HOUR')})"
    )


if __name__ == "__main__":
    setup()
    logger.info("Waiting for next scheduled run... (Ctrl+C to stop)")
    while True:
        schedule.run_pending()
        time.sleep(30)
