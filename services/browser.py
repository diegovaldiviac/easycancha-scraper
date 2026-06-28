from contextlib import contextmanager

from playwright.sync_api import Page, sync_playwright

from services.logger import logger

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)

@contextmanager
def create_browser() -> Page:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=_UA,
            locale="es-CL",
        )
        ctx.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        ctx.add_cookies([{
            "name":   "country",
            "value":  "CL",
            "domain": "www.easycancha.com",
            "path":   "/",
        }])

        page = ctx.new_page()
        logger.info("Browser ready")
        try:
            yield page
        finally:
            browser.close()
            logger.info("Browser closed")
