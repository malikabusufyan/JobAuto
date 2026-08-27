"""EXPERIMENTAL - Y Combinator's "Work at a Startup" board has no public API.
This scrapes the public job list with a normal headed browser. Full job detail
pages require a workatastartup.com login; this only reads what's visible on
the public search/listing page.
"""

import urllib.parse

from jobauto.browser import persistent_page
from jobauto.sources.base import JobListing


def search(keywords: list[str], locations: list[str] | None = None, remote_ok: bool = True) -> list[JobListing]:
    results = []
    search_terms = keywords or [""]
    with persistent_page() as page:
        for keyword in search_terms:
            q = urllib.parse.urlencode({"query": keyword})
            page.goto(f"https://www.workatastartup.com/jobs?{q}", wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            cards = page.locator("[class*='JobPreview'], .job-preview").all()
            for card in cards:
                try:
                    text = card.inner_text().strip()
                    if not text:
                        continue
                    link = card.locator("a").first
                    href = link.get_attribute("href") or ""
                    url = urllib.parse.urljoin("https://www.workatastartup.com", href)
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    title = lines[0] if lines else ""
                    company = lines[1] if len(lines) > 1 else ""
                    job_id = href.rstrip("/").split("/")[-1]
                    results.append(
                        JobListing(
                            source="ycombinator",
                            external_id=job_id or url,
                            title=title,
                            company=company,
                            url=url,
                        )
                    )
                except Exception:
                    continue
    return results
