"""Adzuna official API - free-tier job search aggregator covering the US.
Register at https://developer.adzuna.com/
"""

import requests

from jobauto.config import ADZUNA_APP_ID, ADZUNA_APP_KEY
from jobauto.sources.base import JobListing


def search(keywords: list[str], locations: list[str] | None = None, remote_ok: bool = True, max_pages: int = 2) -> list[JobListing]:
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        return []

    results = []
    search_terms = keywords or [""]
    locs = locations or [""]
    for keyword in search_terms:
        for location in locs:
            for page in range(1, max_pages + 1):
                params = {
                    "app_id": ADZUNA_APP_ID,
                    "app_key": ADZUNA_APP_KEY,
                    "what": keyword,
                    "results_per_page": 50,
                    "content-type": "application/json",
                }
                if location and location.lower() != "remote":
                    params["where"] = location
                try:
                    resp = requests.get(
                        f"https://api.adzuna.com/v1/api/jobs/us/search/{page}",
                        params=params,
                        timeout=20,
                    )
                    resp.raise_for_status()
                except requests.RequestException:
                    continue
                items = resp.json().get("results", [])
                if not items:
                    break
                for job in items:
                    salary = ""
                    if job.get("salary_min") or job.get("salary_max"):
                        salary = f"${job.get('salary_min', 0):.0f}-${job.get('salary_max', 0):.0f}"
                    results.append(
                        JobListing(
                            source="adzuna",
                            external_id=str(job.get("id", "")),
                            title=job.get("title", ""),
                            company=(job.get("company") or {}).get("display_name", ""),
                            url=job.get("redirect_url", ""),
                            location=(job.get("location") or {}).get("display_name", ""),
                            salary=salary,
                            description=job.get("description", ""),
                            posted_at=job.get("created", ""),
                        )
                    )
    return results
