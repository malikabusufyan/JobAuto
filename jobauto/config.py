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

DATA_DIR.mkdir(parents=True, exist_ok=True)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
