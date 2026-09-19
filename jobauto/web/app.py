import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from jobauto import db
from jobauto.config import ROOT_DIR
from jobauto.profile import load_profile
from jobauto.search import run_search

app = FastAPI(title="JobAuto")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

STATUSES = ["new", "generated", "ready", "applied", "interview", "offer", "rejected", "skipped"]
ALL_SOURCE_NAMES = ["greenhouse", "lever", "ashby", "usajobs", "adzuna", "indeed", "linkedin", "dice", "ycombinator"]

# Separate from STATUSES above: this tracks the human's own applied/not-applied intent for a
# job, independent of the generate/apply pipeline state.
APPLICATION_PLANS = ["not_applied", "applied", "will_apply"]
APPLICATION_PLAN_LABELS = {"not_applied": "Not Applied", "applied": "Applied", "will_apply": "Will Apply"}

# Values are days-ago; falls back to discovered_at for postings whose source doesn't supply a
# posted date (see jobauto.sources.dates / db.list_jobs).
POSTED_WITHIN_OPTIONS = ["1", "7", "15", "30"]
POSTED_WITHIN_LABELS = {"1": "Last day", "7": "Last week", "15": "Last 15 days", "30": "Last month"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, status: str = "", max_years: str = "", application_plan: str = "", posted_within: str = ""):
    max_years_int = int(max_years) if max_years.strip().isdigit() else None
    posted_within_int = int(posted_within) if posted_within.strip().isdigit() else None
    rows = db.list_jobs(
        status=status or None,
        max_years=max_years_int,
        application_plan=application_plan or None,
        posted_within_days=posted_within_int,
    )
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "jobs": rows,
            "statuses": STATUSES,
            "sources": ALL_SOURCE_NAMES,
            "active_status": status,
            "active_max_years": max_years,
            "application_plans": APPLICATION_PLANS,
            "application_plan_labels": APPLICATION_PLAN_LABELS,
            "active_application_plan": application_plan,
            "posted_within_options": POSTED_WITHIN_OPTIONS,
            "posted_within_labels": POSTED_WITHIN_LABELS,
            "active_posted_within": posted_within,
        },
    )


@app.post("/search")
def search(sources: list[str] = Form(...)):
    profile = load_profile()
    run_search(profile, sources)
    return RedirectResponse("/", status_code=303)


@app.post("/jobs/add")
def add_job(url: str = Form(...), title: str = Form(...), company: str = Form(...), location: str = Form("")):
    db.upsert_job(
        {"source": "manual", "external_id": url, "title": title, "company": company, "url": url, "location": location}
    )
    return RedirectResponse("/", status_code=303)


@app.get("/job/{job_id}", response_class=HTMLResponse)
def job_detail(request: Request, job_id: int):
    job = db.get_job(job_id)
    return templates.TemplateResponse(
        request,
        "job_detail.html",
        {
            "job": job,
            "statuses": STATUSES,
            "application_plans": APPLICATION_PLANS,
            "application_plan_labels": APPLICATION_PLAN_LABELS,
        },
    )


@app.post("/job/{job_id}/generate")
def generate(job_id: int):
    from jobauto.actions import generate_documents_for_job

    generate_documents_for_job(job_id)
    return RedirectResponse(f"/job/{job_id}", status_code=303)


@app.post("/job/{job_id}/status")
def set_status(job_id: int, status: str = Form(...)):
    db.set_status(job_id, status)
    return RedirectResponse(f"/job/{job_id}", status_code=303)


@app.post("/job/{job_id}/application-plan")
def set_application_plan(request: Request, job_id: int, application_plan: str = Form(...)):
    db.set_application_plan(job_id, application_plan)
    # Sent from the dropdown in the jobs table as well as the job detail page, so send the
    # user back wherever they made the change (preserving any active list filters) instead of
    # always landing on the detail page.
    referer = request.headers.get("referer")
    return RedirectResponse(referer or "/", status_code=303)


@app.post("/job/{job_id}/apply")
def apply(job_id: int):
    # Runs in a separate process with its own visible browser window; the CLI
    # command pauses for human review before anything is submitted, so this
    # must not block the web server's event loop.
    creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0
    subprocess.Popen(
        [sys.executable, "-m", "jobauto.cli", "apply", str(job_id)],
        cwd=str(ROOT_DIR),
        creationflags=creationflags,
    )
    return RedirectResponse(f"/job/{job_id}", status_code=303)


@app.get("/job/{job_id}/download/{doctype}")
def download(job_id: int, doctype: str):
    job = db.get_job(job_id)
    path_map = {
        "resume_pdf": job["resume_pdf_path"],
        "resume_docx": job["resume_docx_path"],
        "cover_letter_pdf": job["cover_letter_pdf_path"],
    }
    path = path_map.get(doctype)
    if not path:
        return HTMLResponse("Not generated yet", status_code=404)
    return FileResponse(path)
