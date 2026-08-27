"""EXPERIMENTAL - Indeed has no free public search API, so this scrapes their
public search results page with a normal headed browser (no login, no stealth
tricks, no headless mode). Indeed's markup changes often and it does rate-limit
aggressive traffic, so treat this as best-effort: it may return zero results
if their layout has shifted since this was written. Prefer the official-API
sources (greenhouse/lever/ashby/usajobs/adzuna) for anything you depend on.
"""

import time
import urllib.parse

from jobauto.browser import persistent_page
from jobauto.sources.base import JobListing


def search(keywords: list[str], locations: list[str] | None = None, remote_ok: bool = True, max_pages: int = 2) -> list[JobListing]:
    results = []
    search_terms = keywords or [""]
    locs = locations or [""]
    with persistent_page() as page:
        for keyword in search_terms:
            for location in locs:
                for page_num in range(max_pages):
                    q = urllib.parse.urlencode(
                        {"q": keyword, "l": "" if location.lower() == "remote" else location,
                         "start": page_num * 10, "sort": "date"}
                    )
                    page.goto(f"https://www.indeed.com/jobs?{q}", wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)
                    cards = page.locator("div.job_seen_beacon").all()
                    if not cards:
                        break
                    for card in cards:
                        try:
                            title_el = card.locator("h2.jobTitle a")
                            title = title_el.inner_text().strip()
                            href = title_el.get_attribute("href") or ""
                            url = urllib.parse.urljoin("https://www.indeed.com", href)
                            company = card.locator("[data-testid='company-name']").inner_text().strip()
                            job_location = card.locator("[data-testid='text-location']").inner_text().strip()
                            job_id = urllib.parse.parse_qs(urllib.parse.urlparse(href).query).get("jk", [href])[0]
                            results.append(
                                JobListing(
                                    source="indeed",
                                    external_id=job_id,
                                    title=title,
                                    company=company,
                                    url=url,
                                    location=job_location,
                                    remote="remote" in job_location.lower(),
                                )
                            )
                        except Exception:
                            continue
                    time.sleep(1.5)
    return results
