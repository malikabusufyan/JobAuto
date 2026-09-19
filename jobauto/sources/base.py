import re
from dataclasses import dataclass, field


@dataclass
class JobListing:
    source: str
    external_id: str
    title: str
    company: str
    url: str
    location: str = ""
    remote: bool = False
    salary: str = ""
    description: str = ""
    posted_at: str = ""

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "external_id": self.external_id,
            "title": self.title,
            "company": self.company,
            "url": self.url,
            "location": self.location,
            "remote": self.remote,
            "salary": self.salary,
            "description": self.description,
            "posted_at": self.posted_at,
        }


def matches_keywords(text: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    lowered = text.lower()
    return any(k.lower() in lowered for k in keywords)


def excludes_keywords(text: str, exclude: list[str]) -> bool:
    if not exclude:
        return False
    lowered = text.lower()
    return any(k.lower() in lowered for k in exclude)


# Companies on Greenhouse/Lever/Ashby often post every office's openings on the same board
# (Figma's "Software Engineer" list includes London and Tel Aviv, Palantir's includes Japan,
# Norway, Korea...), so keyword matching alone doesn't keep results to the US. This is a
# best-effort location heuristic, not a guarantee - unusual formats can slip through either way.
_NON_US_LOCATION_MARKERS = [
    # countries / regions
    "india", "united kingdom", "uk", "england", "scotland", "wales", "ireland",
    "canada", "germany", "france", "spain", "italy", "netherlands", "belgium",
    "switzerland", "austria", "poland", "sweden", "norway", "denmark", "finland",
    "portugal", "greece", "israel", "uae", "united arab emirates", "singapore",
    "japan", "china", "hong kong", "taiwan", "south korea", "korea", "australia",
    "new zealand", "brazil", "argentina", "chile", "colombia", "mexico",
    "philippines", "vietnam", "thailand", "indonesia", "malaysia", "south africa",
    "nigeria", "kenya", "egypt", "turkey", "russia", "ukraine", "romania",
    "czech", "hungary", "europe", "emea", "apac", "latam", "latin america",
    # commonly-seen non-US cities on these boards
    "noida", "hyderabad", "bangalore", "bengaluru", "mumbai", "delhi", "pune",
    "chennai", "gurgaon", "gurugram", "london", "manchester", "dublin",
    "toronto", "vancouver", "montreal", "berlin", "munich", "paris", "madrid",
    "barcelona", "milan", "rome", "amsterdam", "brussels", "zurich", "geneva",
    "vienna", "warsaw", "stockholm", "oslo", "copenhagen", "helsinki", "lisbon",
    "athens", "tel aviv", "dubai", "tokyo", "osaka", "beijing", "shanghai",
    "seoul", "sydney", "melbourne", "auckland", "sao paulo", "mexico city",
    "bogota", "manila", "bangkok", "jakarta", "kuala lumpur", "johannesburg",
    "cairo", "istanbul", "moscow", "budapest",
]

_US_STATE_NAMES = [
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana", "maine",
    "maryland", "massachusetts", "michigan", "minnesota", "mississippi",
    "missouri", "montana", "nebraska", "nevada", "new hampshire", "new jersey",
    "new mexico", "new york", "north carolina", "north dakota", "ohio",
    "oklahoma", "oregon", "pennsylvania", "rhode island", "south carolina",
    "south dakota", "tennessee", "texas", "utah", "vermont", "virginia",
    "washington", "west virginia", "wisconsin", "wyoming",
]

# Major US cities frequently listed without a state suffix (e.g. "San Francisco" instead of
# "San Francisco, CA") - without these, plain city names fell through to the non-US default and
# were wrongly treated as foreign. Not exhaustive of every US city; covers common tech hubs.
_US_CITIES = [
    "san francisco", "bay area", "silicon valley", "new york city", "nyc", "manhattan",
    "brooklyn", "queens", "seattle", "boston", "cambridge, ma", "chicago", "austin",
    "denver", "portland", "miami", "atlanta", "dallas", "houston", "phoenix",
    "philadelphia", "san diego", "san jose", "oakland", "sacramento", "minneapolis",
    "detroit", "pittsburgh", "charlotte", "nashville", "raleigh", "durham",
    "salt lake city", "las vegas", "orlando", "tampa", "baltimore", "columbus",
    "indianapolis", "milwaukee", "kansas city", "st. louis", "cincinnati", "cleveland",
    "memphis", "louisville", "albuquerque", "tucson", "fresno", "omaha",
    "colorado springs", "virginia beach", "oklahoma city", "tulsa", "wichita",
    "arlington, va", "bakersfield", "honolulu", "anchorage", "el paso", "san antonio",
    "fort worth", "jacksonville", "boise", "richmond", "spokane", "tacoma", "irvine",
    "santa monica", "palo alto", "mountain view", "sunnyvale", "cupertino",
    "menlo park", "redwood city", "berkeley", "pasadena", "long beach", "anaheim",
    "santa clara", "san mateo",
]

_US_STATE_ABBR_RE = re.compile(r",\s*[a-z]{2}\b")


def is_us_location(location: str, remote: bool = False) -> bool:
    loc = (location or "").strip().lower()
    if not loc:
        return True  # no location info at all - don't over-filter on absence of data
    if any(marker in loc for marker in _NON_US_LOCATION_MARKERS):
        return False
    if "united states" in loc or re.search(r"\busa\b", loc) or re.search(r"\bu\.s\.?\b", loc):
        return True
    if any(state in loc for state in _US_STATE_NAMES):
        return True
    if any(city in loc for city in _US_CITIES):
        return True
    if _US_STATE_ABBR_RE.search(loc):
        return True
    if remote or "remote" in loc:
        return True  # no non-US marker found and it's remote - lean toward including it
    return False
