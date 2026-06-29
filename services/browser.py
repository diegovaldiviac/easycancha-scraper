import os
from contextlib import contextmanager

from dotenv import load_dotenv
from playwright.sync_api import Page, ProxySettings, sync_playwright

from services.logger import logger

load_dotenv()

_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


def _proxy_config() -> ProxySettings | None:
    """Build a Playwright ProxySettings dict from .env, or return None if PROXY_SERVER is unset."""
    server = os.getenv("PROXY_SERVER")
    if not server:
        return None
    config: ProxySettings = {"server": server}
    username = os.getenv("PROXY_USERNAME")
    password = os.getenv("PROXY_PASSWORD")
    if username:
        config["username"] = username
    if password:
        config["password"] = password
    logger.info(f"Proxy enabled — {server}")
    return config


@contextmanager
def create_browser() -> Page:
    """Context manager that yields a configured Playwright Page and closes the browser on exit.

    Anti-detection measures applied: spoofed Chrome UA, navigator.webdriver=undefined,
    country=CL cookie (skips country selector modal), optional residential proxy.
    """
    proxy = _proxy_config()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
            proxy=proxy,
        )
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=_UA,
            locale="es-CL",
            proxy=proxy,
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
