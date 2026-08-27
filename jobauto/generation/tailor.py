import json

from jobauto.claude_client import ask_json, ask_text

RESUME_SYSTEM = """You are an expert resume writer helping a real candidate tailor their resume
to a specific job posting. You may ONLY rephrase, reorder, re-emphasize, or select among facts
that already appear in the candidate's profile - you must NEVER invent employers, titles, dates,
skills, degrees, or achievements that are not present in the profile. If the profile lacks
something the job wants, simply don't claim it. Favor concrete, quantified language already
implied by the profile's bullets. Keep bullets concise (one line each, action-verb led)."""

RESUME_OUTPUT_SHAPE = """
Return ONLY a JSON object with this exact shape:
{
  "headline": "a short professional title line, e.g. 'Senior Backend Engineer'",
  "summary": "2-3 sentence professional summary tailored to this role",
  "skills": ["ordered/filtered list of skills from the profile, most job-relevant first"],
  "experience": [
    {"company": "", "title": "", "location": "", "start_date": "", "end_date": "",
     "bullets": ["rewritten bullets emphasizing relevance to this job, still truthful"]}
  ],
  "education": [ /* copy the profile's education entries unchanged */ ],
  "projects": [ /* copy or trim the profile's project entries, unchanged facts */ ]
}
"""


def tailor_resume(profile: dict, job: dict) -> dict:
    user = (
        f"{RESUME_OUTPUT_SHAPE}\n\n"
        f"CANDIDATE PROFILE (JSON):\n{json.dumps(profile, indent=2)}\n\n"
        f"JOB POSTING:\nTitle: {job.get('title')}\nCompany: {job.get('company')}\n"
        f"Location: {job.get('location')}\nDescription:\n{job.get('description', '')[:6000]}"
    )
    return ask_json(system=RESUME_SYSTEM, user=user, max_tokens=4000)


COVER_LETTER_SYSTEM = """You are an expert career writer helping a real candidate write a cover
letter for a specific job. You may ONLY reference facts, employers, and achievements that already
appear in the candidate's profile - never invent experience. Write in the candidate's voice: direct,
confident, no cliches like "I am writing to express my interest". 3-4 short paragraphs, plain text,
no markdown, no placeholder brackets. End with a simple sign-off using the candidate's name."""


def generate_cover_letter(profile: dict, job: dict) -> str:
    user = (
        f"CANDIDATE PROFILE (JSON):\n{json.dumps(profile, indent=2)}\n\n"
        f"JOB POSTING:\nTitle: {job.get('title')}\nCompany: {job.get('company')}\n"
        f"Location: {job.get('location')}\nDescription:\n{job.get('description', '')[:6000]}\n\n"
        f"Write the cover letter now."
    )
    return ask_text(system=COVER_LETTER_SYSTEM, user=user, max_tokens=1500)
