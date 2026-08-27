"""Ashby job board public API - no auth needed, no ToS issues.

Supply each company's org slug (from jobs.ashbyhq.com/<slug>) under
preferences.target_companies.ashby.
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
    for slug in companies:
        try:
            resp = requests.get(
                f"https://api.ashbyhq.com/posting-api/job-board/{slug}",
                headers=HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
        except requests.RequestException:
            continue
        for job in resp.json().get("jobs", []):
            description = _strip_html(job.get("descriptionHtml", "")) or job.get("descriptionPlain", "")
            title = job.get("title", "")
            # Match against the title only - see greenhouse.py for why.
            if not matches_keywords(title, keywords) or excludes_keywords(f"{title} {description}", exclude):
                continue
            results.append(
                JobListing(
                    source="ashby",
                    external_id=str(job.get("id", job.get("jobUrl", ""))),
                    title=job.get("title", ""),
                    company=slug,
                    url=job.get("jobUrl") or job.get("applyUrl", ""),
                    location=job.get("location", ""),
                    remote=bool(job.get("isRemote")),
                    description=description,
                    posted_at=job.get("publishedAt", ""),
                )
            )
    return results
