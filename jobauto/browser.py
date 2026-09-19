"""Shared Playwright helpers. Always runs headed (visible) browsers - this tool
never runs headless scraping and never installs stealth/anti-detection plugins.
For sites that require login (LinkedIn), you log in yourself in the opened window;
the tool only reads what's already rendered on screen.
"""

from contextlib import contextmanager
from pathlib import Path

from jobauto.config import (
    CHROME_PROFILE_DIRECTORY,
    CHROME_REMOTE_DEBUGGING_PORT,
    CHROME_USER_DATA_DIR,
    DATA_DIR,
)

BROWSER_PROFILE_DIR = DATA_DIR / "browser_profile"


@contextmanager
def persistent_page(headless: bool = False):
    """A browser context backed by a persistent profile directory, so logins
    (e.g. LinkedIn) survive between runs without re-entering credentials.

    If CHROME_REMOTE_DEBUGGING_PORT is set in .env, this attaches to a Chrome window
    that's already running (see scripts/launch-chrome-debug.ps1) instead of launching a
    new one - only the tab this opens is ever closed, never the browser itself. Otherwise,
    if CHROME_USER_DATA_DIR is set, this reuses your real, already-signed-in Chrome profile
    instead of the tool's own blank one - see the comments in config.py. That mode launches
    a separate process, so your regular Chrome must be fully closed first: Chrome locks a
    profile directory to one running process at a time."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        if CHROME_REMOTE_DEBUGGING_PORT:
            browser = p.chromium.connect_over_cdp(f"http://localhost:{CHROME_REMOTE_DEBUGGING_PORT}")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            try:
                yield page
            finally:
                page.close()
            return
        if CHROME_USER_DATA_DIR:
            context = p.chromium.launch_persistent_context(
                CHROME_USER_DATA_DIR,
                channel="chrome",
                headless=headless,
                viewport={"width": 1280, "height": 900},
                args=[f"--profile-directory={CHROME_PROFILE_DIRECTORY}"],
            )
        else:
            BROWSER_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
            context = p.chromium.launch_persistent_context(
                str(BROWSER_PROFILE_DIR), headless=headless, viewport={"width": 1280, "height": 900}
            )
        page = context.pages[0] if context.pages else context.new_page()
        try:
            yield page
        finally:
            context.close()
