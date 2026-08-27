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
