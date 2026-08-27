"""EXPERIMENTAL, HIGHER RISK - LinkedIn's User Agreement prohibits automated
scraping, and it actively detects and can restrict/ban accounts that trigger
its automation heuristics. This module does NOT automate login and does NOT
use any stealth/anti-detection techniques - it opens a normal, visible browser
window, asks *you* to log in and browse like a human, and only reads whatever
is already rendered on screen when called. Use at your own risk to your
LinkedIn account; consider skipping this source entirely and relying on the
official-API sources instead.
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
                q = urllib.parse.urlencode(
                    {"keywords": keyword, "location": location, "f_TPR": "r86400"}
                )
                page.goto(f"https://www.linkedin.com/jobs/search/?{q}", wait_until="domcontentloaded")
                page.wait_for_timeout(2000)

                if "login" in page.url or page.locator("input#username").count() > 0:
                    input(
                        "\n>>> Please log in to LinkedIn in the opened browser window, "
                        "then press Enter here to continue...\n"
                    )
                    page.goto(f"https://www.linkedin.com/jobs/search/?{q}", wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)

                cards = page.locator("div.base-card").all()
                for card in cards:
                    try:
                        title = card.locator(".base-search-card__title").inner_text().strip()
                        company = card.locator(".base-search-card__subtitle").inner_text().strip()
                        job_location = card.locator(".job-search-card__location").inner_text().strip()
                        url = card.locator("a.base-card__full-link").get_attribute("href") or ""
                        external_id = url.rstrip("/").split("-")[-1].split("?")[0]
                        results.append(
                            JobListing(
                                source="linkedin",
                                external_id=external_id or url,
                                title=title,
                                company=company,
                                url=url,
                                location=job_location,
                                remote="remote" in job_location.lower(),
                            )
                        )
                    except Exception:
                        continue
    return results
