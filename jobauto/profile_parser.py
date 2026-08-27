from pathlib import Path

from jobauto.claude_client import ask_json

PROFILE_SCHEMA_INSTRUCTIONS = """
Extract the candidate's information from the resume text into this exact JSON shape
(omit nothing; use "" or [] for fields you cannot find - never invent facts not in the text):

{
  "personal": {
    "full_name": "", "email": "", "phone": "", "location": "",
    "linkedin": "", "github": "", "portfolio": "",
    "work_authorization": "", "willing_to_relocate": false, "willing_to_sponsor_needed": false
  },
  "summary": "",
  "skills": [""],
  "experience": [
    {"company": "", "title": "", "location": "", "start_date": "YYYY-MM", "end_date": "YYYY-MM or Present",
     "bullets": [""]}
  ],
  "education": [
    {"institution": "", "degree": "", "field": "", "start_date": "YYYY-MM", "end_date": "YYYY-MM", "gpa": ""}
  ],
  "projects": [{"name": "", "description": "", "bullets": [""]}],
  "certifications": [""],
  "achievements": [""],
  "preferences": {
    "target_titles": [""], "target_locations": [""], "remote_ok": true, "min_salary": 0,
    "target_companies": {"greenhouse": [], "lever": [], "ashby": []}, "keywords_exclude": []
  }
}

For "preferences", make a reasonable guess at target_titles from the candidate's most recent
title(s); leave target_companies empty and min_salary at 0 - those need the human to fill in.
Leave "work_authorization" and "willing_to_sponsor_needed" exactly as "" / false unless the resume
explicitly states them - never infer visa/citizenship status from nationality, employer location,
or school; this is a legal question only the candidate can answer.
Respond with ONLY the JSON object, no commentary, no markdown fences.
"""


def extract_text_from_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif suffix == ".docx":
        import docx

        doc = docx.Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    elif suffix == ".txt":
        return path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"Unsupported resume file type: {suffix} (use .pdf, .docx, or .txt)")


def parse_resume_to_profile(path: Path) -> dict:
    text = extract_text_from_file(path)
    if not text.strip():
        raise ValueError(f"Could not extract any text from {path}")
    return ask_json(
        system="You are a precise resume-parsing assistant. You only extract facts that are "
        "literally present in the given text; you never fabricate employers, dates, or skills.",
        user=f"{PROFILE_SCHEMA_INSTRUCTIONS}\n\nRESUME TEXT:\n{text}",
        max_tokens=4000,
    )
