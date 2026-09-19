from jobauto import db
from jobauto.sources import ALL_SOURCES
from jobauto.sources.base import excludes_keywords, is_us_location
from jobauto.sources.experience import matches_experience_range

DIRECTORY_SOURCES = {"greenhouse", "lever", "ashby"}  # need target_companies, not keywords
KEYWORD_SOURCES = {"usajobs", "adzuna", "indeed", "linkedin", "dice", "ycombinator"}

# usajobs and adzuna are already scoped to the US at the API level (usajobs is US federal-only;
# adzuna is queried against its /us/ endpoint) - the location heuristic only needs to run on
# sources that pull from company boards spanning every office worldwide.
_NEEDS_US_FILTER = {"greenhouse", "lever", "ashby", "indeed", "linkedin", "dice", "ycombinator"}


def run_search(profile: dict, source_names: list[str]) -> dict:
    prefs = profile.get("preferences", {})
    keywords = prefs.get("target_titles", [])
    locations = prefs.get("target_locations", [])
    remote_ok = prefs.get("remote_ok", True)
    exclude = prefs.get("keywords_exclude", [])
    target_companies = prefs.get("target_companies", {})
    us_only = prefs.get("us_only", True)
    max_years_experience = prefs.get("max_years_experience")

    added = 0
    seen = 0
    filtered_out_non_us = 0
    filtered_out_excluded = 0
    filtered_out_over_experience = 0
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
            if us_only and name in _NEEDS_US_FILTER and not is_us_location(listing.location, listing.remote):
                filtered_out_non_us += 1
                continue
            # Applied here (title only, not full description) for every source, since only
            # greenhouse/lever/ashby apply `exclude` themselves, and even they check the full
            # description text, which can false-positive on incidental mentions - e.g. a junior
            # role's description mentioning "reports to senior leadership".
            if excludes_keywords(listing.title, exclude):
                filtered_out_excluded += 1
                continue
            if max_years_experience is not None and not matches_experience_range(
                listing.title, listing.description or "", max_years_experience
            ):
                filtered_out_over_experience += 1
                continue
            _, created = db.upsert_job(listing.to_dict())
            if created:
                added += 1

    return {
        "seen": seen,
        "added": added,
        "filtered_out_non_us": filtered_out_non_us,
        "filtered_out_excluded": filtered_out_excluded,
        "filtered_out_over_experience": filtered_out_over_experience,
        "sources_run": source_names,
        "errors": errors,
    }
