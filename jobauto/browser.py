"""Shared Playwright helpers. Always runs headed (visible) browsers - this tool
never runs headless scraping and never installs stealth/anti-detection plugins.
For sites that require login (LinkedIn), you log in yourself in the opened window;
the tool only reads what's already rendered on screen.
"""

from contextlib import contextmanager
from pathlib import Path

from jobauto.config import DATA_DIR

BROWSER_PROFILE_DIR = DATA_DIR / "browser_profile"


@contextmanager
def persistent_page(headless: bool = False):
    """A browser context backed by a persistent profile directory, so logins
    (e.g. LinkedIn) survive between runs without re-entering credentials."""
    from playwright.sync_api import sync_playwright

    BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(BROWSER_PROFILE_DIR), headless=headless, viewport={"width": 1280, "height": 900}
        )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            yield page
        finally:
            context.close()
