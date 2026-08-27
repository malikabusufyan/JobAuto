"""Greenhouse job board public API - no auth needed, no ToS issues.

Greenhouse has no cross-company search, so you must supply the "board token"
for each company you're targeting (from the careers page URL:
boards.greenhouse.io/<token>). Add tokens under preferences.target_companies.greenhouse
in your profile.yaml.
"""

import re

import requests

from jobauto.config import CONTACT_EMAIL
from jobauto.sources.base import JobListing, matches_keywords, excludes_keywords

HEADERS = {"User-Agent": f"JobAuto personal job-search tool ({CONTACT_EMAIL})"}


def _strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").strip()


def search(companies: list[str], keywords: list[str] | None = None, exclude: list[str] | None = None) -> list[JobListing]:
    results = []
    for token in companies:
        try:
            resp = requests.get(
                f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                params={"content": "true"},
                headers=HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
        except requests.RequestException:
            continue
        for job in resp.json().get("jobs", []):
            description = _strip_html(job.get("content", ""))
            title = job.get("title", "")
            # Match against the title only - descriptions are long enough that generic terms
            # like "software engineer" show up in almost every posting's boilerplate.
            if not matches_keywords(title, keywords) or excludes_keywords(f"{title} {description}", exclude):
                continue
            results.append(
                JobListing(
                    source="greenhouse",
                    external_id=str(job["id"]),
                    title=job.get("title", ""),
                    company=token,
                    url=job.get("absolute_url", ""),
                    location=(job.get("location") or {}).get("name", ""),
                    description=description,
                    posted_at=job.get("updated_at", ""),
                )
            )
    return results
