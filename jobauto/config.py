import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
GENERATED_DIR = DATA_DIR / "generated"
DB_PATH = DATA_DIR / "jobauto.sqlite3"
PROFILE_PATH = DATA_DIR / "profile.yaml"

load_dotenv(ROOT_DIR / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
USAJOBS_API_KEY = os.getenv("USAJOBS_API_KEY", "")
USAJOBS_USER_AGENT_EMAIL = os.getenv("USAJOBS_USER_AGENT_EMAIL", "")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "jobauto-user@example.com")

# Resume/cover-letter tailoring is a well-defined, structured writing task, not
# a task that needs top-tier reasoning - Haiku handles it well at a small
# fraction of Opus's cost (roughly $0.01-0.02 per job vs. $0.20-0.40). Override
# with CLAUDE_MODEL in .env if you want higher-effort writing and don't mind
# the extra cost (e.g. claude-sonnet-5 or claude-opus-5).
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5")

# Optional: point the apply/search browser at your real, already-signed-in Chrome profile
# instead of a blank automated one. Google/Microsoft block sign-in attempts from a fresh
# Playwright-driven window ("this browser or app may not be secure"); reusing a profile
# that's already logged in avoids triggering that check at all, since no new OAuth handshake
# happens. Find your profile folder name via chrome://version -> "Profile Path" (the last
# path segment, e.g. "Default" or "Profile 1"). Leave CHROME_USER_DATA_DIR unset to use the
# tool's own isolated profile at data/browser_profile instead (the previous default).
CHROME_USER_DATA_DIR = os.getenv("CHROME_USER_DATA_DIR", "")
CHROME_PROFILE_DIRECTORY = os.getenv("CHROME_PROFILE_DIRECTORY", "Default")

# Optional, and takes priority over CHROME_USER_DATA_DIR above: instead of launching a new
# Chrome process, attach to a Chrome window that's already running with this remote-debugging
# port open (see scripts/launch-chrome-debug.ps1). Opens a new tab in your existing session
# and only ever closes that tab - your browser, its other tabs, and any other open windows
# are never touched, so you don't have to close Chrome before running JobAuto. Trade-off:
# that debugging port gives any local process full control of the browser (read cookies,
# navigate, run JS) for as long as Chrome stays open with it - only enable it if you're okay
# with that on this machine.
CHROME_REMOTE_DEBUGGING_PORT = os.getenv("CHROME_REMOTE_DEBUGGING_PORT", "")

DATA_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
