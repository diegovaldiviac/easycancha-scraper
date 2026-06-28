"""
Abstract booking service for easycancha.

All configuration is read from .env — this module contains no hardcoded
club, sport, day, or hour values. A second user only needs to change their
.env to point at a different club URL and slot.

Required .env keys:
    BOOKING_URL   — e.g. https://www.easycancha.com/book/clubs/59/sports/1/filter
    TARGET_DAY    — weekday name in English, e.g. "Saturday"
    TARGET_HOUR   — 24-h time, e.g. "11:00"
"""

import os
import time as _time
from datetime import date, timedelta

from dotenv import load_dotenv
from playwright.sync_api import Page, TimeoutError as PWT

from services.logger import logger

load_dotenv()

_BOOKING_URL = os.getenv("BOOKING_URL")
_TARGET_DAY  = os.getenv("TARGET_DAY",  "Saturday")
_TARGET_HOUR = os.getenv("TARGET_HOUR", "11:00")

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2,
    "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
}

# Short Spanish day abbreviations as rendered in easycancha's date strip
_ES_SHORT = {
    0: "LUN.", 1: "MAR.", 2: "MIÉ.", 3: "JUE.",
    4: "VIE.", 5: "SÁB.", 6: "DOM.",
}


# ── public API ─────────────────────────────────────────────────────────────────

def next_target_date() -> date:
    """Return the next calendar date that matches TARGET_DAY."""
    target_weekday = _WEEKDAYS[_TARGET_DAY.lower()]
    today = date.today()
    days_ahead = (target_weekday - today.weekday()) % 7 or 7
    return today + timedelta(days=days_ahead)


def book(page: Page, target: date) -> None:
    """
    Book a court for *target* at TARGET_HOUR using the authenticated *page*.

    Steps (confirmed against live site):
      1. Navigate to BOOKING_URL
      2. Select the target date in the calendar strip (.cds-day)
      3. Select the target hour in the time strip (.hour_item)
      4. Click "Siguiente" (processFilters)
      5. Select the first available court (preBookAndSelectCourtV2)
      6. Confirm the booking
    """
    logger.info(f"Booking {_TARGET_DAY} {target} at {_TARGET_HOUR}")
    page.goto(_BOOKING_URL, wait_until="networkidle", timeout=30_000)

    _select_date(page, target)
    _select_time(page)
    _click_siguiente(page)
    _select_court(page)
    _confirm(page)


# ── internal steps ─────────────────────────────────────────────────────────────

def _select_date(page: Page, target: date) -> None:
    day_num = target.day
    day_es  = _ES_SHORT[target.weekday()]   # e.g. "SÁB."
    logger.info(f"Selecting date — {day_num} {day_es} ({target})")

    def _try_click() -> bool:
        for d in page.locator(".cds-day").all():
            try:
                num = d.locator(".cds-day-number").inner_text().strip()
                txt = d.locator(".cds-day-text").inner_text().strip().upper()
                if str(day_num) == num and day_es.upper() in txt:
                    d.click()
                    _time.sleep(1.5)
                    logger.info(f"Date selected: {num} {txt}")
                    return True
            except Exception:
                continue
        return False

    if _try_click():
        return

    # Advance through calendar weeks until the target date appears (up to 4 weeks)
    for _ in range(4):
        page.locator("[ng-click='next()']").click()
        _time.sleep(1)
        if _try_click():
            return

    logger.warning(f"Date {target} not found in calendar — booking window may not be open")


def _select_time(page: Page) -> None:
    logger.info(f"Selecting time slot {_TARGET_HOUR}")
    _time.sleep(1)

    for h in page.locator(".hour_item").all():
        try:
            txt = h.locator(".hour_item_number").inner_text().strip()
            if txt == _TARGET_HOUR:
                h.click()
                _time.sleep(0.5)
                logger.info(f"Time {_TARGET_HOUR} selected")
                return
        except Exception:
            continue

    raise RuntimeError(
        f"Time slot {_TARGET_HOUR} is not available yet — "
        "the booking window for this date may not have opened"
    )


def _click_siguiente(page: Page) -> None:
    logger.info("Clicking Siguiente")
    page.locator("[ng-click='processFilters()']").click()
    page.wait_for_load_state("networkidle")
    _time.sleep(1.5)


def _select_court(page: Page) -> None:
    logger.info("Selecting court")
    courts = page.locator("[ng-click*='preBookAndSelectCourtV2']").all()

    if not courts:
        raise RuntimeError("No courts found — check that the slot is still available")

    for c in courts:
        try:
            logger.info(f"  Available: {c.inner_text().strip().replace(chr(10), ' ')}")
        except Exception:
            pass

    courts[0].click()
    page.wait_for_load_state("networkidle")
    _time.sleep(1.5)
    logger.info("Court selected")


def _confirm(page: Page) -> None:
    logger.info("Looking for confirmation button")

    for selector in (
        'button:has-text("Confirmar")',
        'button:has-text("Reservar")',
        'button:has-text("Pagar")',
        '[ng-click*="confirm"]',
        '[ng-click*="pagar"]',
        '[ng-click*="pay"]',
    ):
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=3_000):
                btn.click()
                page.wait_for_load_state("networkidle")
                logger.info("Booking confirmed!")
                return
        except PWT:
            continue

    logger.warning("No confirm button found — the last step may need a manual selector update")
