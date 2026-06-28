import os

from dotenv import load_dotenv
from playwright.sync_api import Page, TimeoutError as PWT

from services.logger import logger

load_dotenv()

_EMAIL     = os.getenv("EMAIL")
_PASSWORD  = os.getenv("PASSWORD")
_LOGIN_URL = "https://www.easycancha.com/login"


def login(page: Page) -> None:
    """
    Authenticate to easycancha using credentials from .env.

    The country=CL cookie is pre-set by create_browser(), so the site lands
    directly on the login form — no country selector, no modal.

    Flow:
      1. GET /login  →  lands on login form (country already known via cookie)
      2. Type email + password (AngularJS ng-model requires real keystrokes)
      3. Click "Ingresar"  →  redirects to /book/... on success

    Raises RuntimeError if login fails.
    """
    logger.info("Authenticating")
    page.goto(_LOGIN_URL, wait_until="networkidle", timeout=30_000)
    _submit_credentials(page)


def _submit_credentials(page: Page) -> None:
    # AngularJS ng-model bindings require real keystrokes — page.fill() won't trigger them
    email_input = page.locator('input[type="email"]')
    email_input.click()
    email_input.type(_EMAIL, delay=30)

    pass_input = page.locator('input[type="password"]')
    pass_input.click()
    pass_input.type(_PASSWORD, delay=30)

    page.locator("button.login-btn").click()

    try:
        page.wait_for_url("**/book**", timeout=15_000)
        logger.info(f"Login successful — {page.url}")
    except PWT:
        raise RuntimeError(
            f"Login failed (still at {page.url}). "
            "Check EMAIL and PASSWORD in .env."
        )
