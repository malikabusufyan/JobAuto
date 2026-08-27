"""EXPERIMENTAL - Dice has no free public search API, so this scrapes their
public search results page with a normal headed browser. Same caveats as
indeed.py: markup drifts, treat results as best-effort.
"""

import urllib.parse

from jobauto.browser import persistent_page
from jobauto.sources.base import JobListing


def search(keywords: list[str], locations: list[str] | None = None, remote_ok: bool = True) -> list[JobListing]:
    results = []
    search_terms = keywords or [""]
    locs = locations or [""]
    with persistent_page() as page:
        for keyword in search_terms:
            for location in locs:
                params = {"q": keyword}
                if location and location.lower() != "remote":
                    params["location"] = location
                if remote_ok:
                    params["filters.isRemote"] = "true"
                q = urllib.parse.urlencode(params)
                page.goto(f"https://www.dice.com/jobs?{q}", wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                cards = page.locator("dhi-search-card, [data-cy='card-title-link']").all()
                for card in cards:
                    try:
                        link = card.locator("a").first if card.locator("a").count() else card
                        title = link.inner_text().strip()
                        href = link.get_attribute("href") or ""
                        url = urllib.parse.urljoin("https://www.dice.com", href)
                        job_id = href.rstrip("/").split("/")[-1]
                        results.append(
                            JobListing(
                                source="dice",
                                external_id=job_id,
                                title=title,
                                company="",
                                url=url,
                                location=location,
                                remote=remote_ok,
                            )
                        )
                    except Exception:
                        continue
    return results
