from jobauto import db
from jobauto.sources import ALL_SOURCES

DIRECTORY_SOURCES = {"greenhouse", "lever", "ashby"}  # need target_companies, not keywords
KEYWORD_SOURCES = {"usajobs", "adzuna", "indeed", "linkedin", "dice", "ycombinator"}


def run_search(profile: dict, source_names: list[str]) -> dict:
    prefs = profile.get("preferences", {})
    keywords = prefs.get("target_titles", [])
    locations = prefs.get("target_locations", [])
    remote_ok = prefs.get("remote_ok", True)
    exclude = prefs.get("keywords_exclude", [])
    target_companies = prefs.get("target_companies", {})

    added = 0
    seen = 0
    errors = {}
    for name in source_names:
        source = ALL_SOURCES.get(name)
        if source is None:
            errors[name] = "unknown source"
            continue
        try:
            if name in DIRECTORY_SOURCES:
                companies = target_companies.get(name, [])
                if not companies:
                    continue
                listings = source.search(companies, keywords=keywords, exclude=exclude)
            else:
                listings = source.search(keywords=keywords, locations=locations, remote_ok=remote_ok)
        except Exception as e:
            errors[name] = str(e)
            continue

        for listing in listings:
            seen += 1
            _, created = db.upsert_job(listing.to_dict())
            if created:
                added += 1

    return {"seen": seen, "added": added, "sources_run": source_names, "errors": errors}
