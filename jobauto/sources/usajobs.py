"""USAJobs.gov official API - US federal government jobs. Free key at
https://developer.usajobs.gov/APIRequest/Index
"""

import requests

from jobauto.config import USAJOBS_API_KEY, USAJOBS_USER_AGENT_EMAIL
from jobauto.sources.base import JobListing


def search(keywords: list[str], locations: list[str] | None = None, remote_ok: bool = True) -> list[JobListing]:
    if not USAJOBS_API_KEY or not USAJOBS_USER_AGENT_EMAIL:
        return []

    headers = {
        "Host": "data.usajobs.gov",
        "User-Agent": USAJOBS_USER_AGENT_EMAIL,
        "Authorization-Key": USAJOBS_API_KEY,
    }
    results = []
    search_terms = keywords or [""]
    locs = locations or [""]
    for keyword in search_terms:
        for location in locs:
            params = {"Keyword": keyword, "ResultsPerPage": 100}
            if location and location.lower() != "remote":
                params["LocationName"] = location
            try:
                resp = requests.get(
                    "https://data.usajobs.gov/api/search", params=params, headers=headers, timeout=20
                )
                resp.raise_for_status()
            except requests.RequestException:
                continue
            for item in resp.json().get("SearchResult", {}).get("SearchResultItems", []):
                d = item.get("MatchedObjectDescriptor", {})
                positions = d.get("PositionLocation", [])
                location_name = positions[0]["LocationName"] if positions else ""
                remuneration = d.get("PositionRemuneration", [])
                salary = ""
                if remuneration:
                    r = remuneration[0]
                    salary = f"${r.get('MinimumRange', '')}-${r.get('MaximumRange', '')} {r.get('RateIntervalCode', '')}"
                results.append(
                    JobListing(
                        source="usajobs",
                        external_id=str(d.get("PositionID", item.get("MatchedObjectId", ""))),
                        title=d.get("PositionTitle", ""),
                        company=d.get("OrganizationName", ""),
                        url=d.get("PositionURI", ""),
                        location=location_name,
                        salary=salary,
                        description=d.get("UserArea", {}).get("Details", {}).get("JobSummary", ""),
                        posted_at=d.get("PublicationStartDate", ""),
                    )
                )
    return results
