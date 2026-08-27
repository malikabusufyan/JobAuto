import json
from pathlib import Path

from jobauto import db
from jobauto.config import GENERATED_DIR
from jobauto.generation.render import render_cover_letter_pdf, render_resume_docx, render_resume_pdf
from jobauto.generation.tailor import generate_cover_letter, tailor_resume
from jobauto.profile import load_profile


def _job_dir(job_row) -> Path:
    safe_company = "".join(c if c.isalnum() else "_" for c in job_row["company"])[:40]
    return GENERATED_DIR / f"{job_row['id']}_{safe_company}"


def generate_documents_for_job(job_id: int) -> dict:
    """Calls the Anthropic API (via ANTHROPIC_API_KEY) to do the tailoring, then renders."""
    job_row = db.get_job(job_id)
    if not job_row:
        raise ValueError(f"No job with id {job_id}")
    profile = load_profile()
    job = dict(job_row)

    tailored = tailor_resume(profile, job)
    letter_text = generate_cover_letter(profile, job)
    return save_generated_documents(job_id, tailored, letter_text)


def save_generated_documents(job_id: int, tailored: dict, letter_text: str) -> dict:
    """Renders and stores documents from already-tailored content, without calling any API.
    Use this when a Claude Code session (running under a Claude.ai subscription, not the
    metered API) has done the tailoring itself and just needs the result rendered/saved."""
    job_row = db.get_job(job_id)
    if not job_row:
        raise ValueError(f"No job with id {job_id}")
    profile = load_profile()
    job = dict(job_row)

    out_dir = _job_dir(job_row)
    resume_pdf = out_dir / "resume.pdf"
    resume_docx = out_dir / "resume.docx"
    cover_pdf = out_dir / "cover_letter.pdf"

    render_resume_pdf(profile, tailored, resume_pdf)
    render_resume_docx(profile, tailored, resume_docx)
    render_cover_letter_pdf(profile, job, letter_text, cover_pdf)

    db.update_job(
        job_id,
        status="generated",
        resume_pdf_path=str(resume_pdf),
        resume_docx_path=str(resume_docx),
        cover_letter_pdf_path=str(cover_pdf),
        tailoring_json=json.dumps({"resume": tailored, "cover_letter": letter_text}),
    )
    return {"resume_pdf": resume_pdf, "resume_docx": resume_docx, "cover_letter_pdf": cover_pdf}


def apply_to_job(job_id: int):
    from jobauto.autofill.filler import fill_application

    job_row = db.get_job(job_id)
    if not job_row:
        raise ValueError(f"No job with id {job_id}")
    if not job_row["resume_pdf_path"]:
        raise ValueError("Generate the tailored resume/cover letter first.")

    profile = load_profile()
    fill_application(
        job_url=job_row["url"],
        profile=profile,
        resume_path=Path(job_row["resume_pdf_path"]),
        cover_letter_path=Path(job_row["cover_letter_pdf_path"]) if job_row["cover_letter_pdf_path"] else None,
    )
    db.set_status(job_id, "applied")
