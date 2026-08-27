from pathlib import Path

import yaml

from jobauto.config import PROFILE_PATH


def load_profile(path: Path | None = None) -> dict:
    p = path or PROFILE_PATH
    if not p.exists():
        raise FileNotFoundError(
            f"No profile found at {p}. Copy data/profile.example.yaml to data/profile.yaml "
            f"and fill it in, or run: python -m jobauto.cli parse-resume <your_resume_file>"
        )
    with open(p, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_profile(profile: dict, path: Path | None = None):
    p = path or PROFILE_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        yaml.safe_dump(profile, f, sort_keys=False, allow_unicode=True, width=100)
