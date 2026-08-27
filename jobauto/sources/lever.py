"""Lever job board public API - no auth needed, no ToS issues.

Like Greenhouse, Lever has no cross-company search. Supply each company's slug
(from jobs.lever.co/<slug>) under preferences.target_companies.lever.
"""

import requests

from jobauto.config import CONTACT_EMAIL
from jobauto.sources.base import JobListing, matches_keywords, excludes_keywords

HEADERS = {"User-Agent": f"JobAuto personal job-search tool ({CONTACT_EMAIL})"}


def search(companies: list[str], keywords: list[str] | None = None, exclude: list[str] | None = None) -> list[JobListing]:
    results = []
    for slug in companies:
        try:
            resp = requests.get(
                f"https://api.lever.co/v0/postings/{slug}",
                params={"mode": "json"},
                headers=HEADERS,
                timeout=20,
            )
            resp.raise_for_status()
        except requests.RequestException:
            continue
        for job in resp.json():
            description = job.get("descriptionPlain") or job.get("description") or ""
            title = job.get("text", "")
            # Match against the title only - see greenhouse.py for why.
            if not matches_keywords(title, keywords) or excludes_keywords(f"{title} {description}", exclude):
                continue
            categories = job.get("categories", {}) or {}
            results.append(
                JobListing(
                    source="lever",
                    external_id=str(job["id"]),
                    title=job.get("text", ""),
                    company=slug,
                    url=job.get("hostedUrl", ""),
                    location=categories.get("location", ""),
                    remote=bool(categories.get("commitment", "").lower() == "remote")
                    or "remote" in (categories.get("location", "") or "").lower(),
                    description=description,
                    posted_at=str(job.get("createdAt", "")),
                )
            )
    return results
