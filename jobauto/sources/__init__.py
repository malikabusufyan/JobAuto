from jobauto.sources.base import JobListing
from jobauto.sources import greenhouse, lever, ashby, usajobs, adzuna

OFFICIAL_API_SOURCES = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "usajobs": usajobs,
    "adzuna": adzuna,
}

try:
    from jobauto.sources import indeed, linkedin, dice, ycombinator

    EXPERIMENTAL_SCRAPER_SOURCES = {
        "indeed": indeed,
        "linkedin": linkedin,
        "dice": dice,
        "ycombinator": ycombinator,
    }
except ImportError:
    # Playwright not installed - experimental scrapers unavailable, official APIs still work.
    EXPERIMENTAL_SCRAPER_SOURCES = {}

ALL_SOURCES = {**OFFICIAL_API_SOURCES, **EXPERIMENTAL_SCRAPER_SOURCES}

__all__ = ["JobListing", "OFFICIAL_API_SOURCES", "EXPERIMENTAL_SCRAPER_SOURCES", "ALL_SOURCES"]
