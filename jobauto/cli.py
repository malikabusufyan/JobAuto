import argparse
import shutil
import sys
from pathlib import Path

from jobauto import db
from jobauto.config import DATA_DIR, PROFILE_PATH


def cmd_init(args):
    db.init_db()
    example = DATA_DIR / "profile.example.yaml"
    if not PROFILE_PATH.exists() and example.exists():
        shutil.copy(example, PROFILE_PATH)
        print(f"Created {PROFILE_PATH} from the example template. Edit it with your real details.")
    else:
        print("Database initialized.")


def cmd_parse_resume(args):
    from jobauto.profile import save_profile
    from jobauto.profile_parser import parse_resume_to_profile

    profile = parse_resume_to_profile(Path(args.file))
    save_profile(profile)
    print(f"Draft profile written to {PROFILE_PATH}")
    print("Review it carefully - especially preferences.target_companies, min_salary, and work_authorization.")


def cmd_search(args):
    from jobauto.profile import load_profile
    from jobauto.search import run_search

    db.init_db()
    profile = load_profile()
    sources = args.sources.split(",") if args.sources else ["greenhouse", "lever", "ashby", "usajobs", "adzuna"]
    result = run_search(profile, sources)
    print(f"Checked sources: {result['sources_run']}")
    print(f"Found {result['seen']} matching listings, {result['added']} new.")
    if result["errors"]:
        print("Errors:")
        for name, err in result["errors"].items():
            print(f"  {name}: {err}")


def cmd_add_job(args):
    db.init_db()
    job_id, created = db.upsert_job(
        {
            "source": "manual",
            "external_id": args.url,
            "title": args.title,
            "company": args.company,
            "url": args.url,
            "location": args.location or "",
            "description": args.description or "",
        }
    )
    print(f"{'Added' if created else 'Already tracked as'} job id {job_id}.")


def cmd_list(args):
    db.init_db()
    rows = db.list_jobs(status=args.status)
    try:
        for row in rows:
            print(f"[{row['id']:>4}] {row['status']:<10} {row['title']} @ {row['company']} ({row['source']}) - {row['url']}")
        print(f"\n{len(rows)} job(s).")
    except (BrokenPipeError, OSError):
        pass  # downstream reader (e.g. `| head`) closed the pipe early


def cmd_generate(args):
    from jobauto.actions import generate_documents_for_job

    paths = generate_documents_for_job(args.job_id)
    print("Generated:")
    for key, path in paths.items():
        print(f"  {key}: {path}")


def cmd_render_manual(args):
    import json as json_module

    from jobauto.actions import save_generated_documents

    tailored = json_module.loads(Path(args.tailored_json).read_text(encoding="utf-8"))
    letter_text = Path(args.cover_letter).read_text(encoding="utf-8")
    paths = save_generated_documents(args.job_id, tailored, letter_text)
    print("Rendered from manually-supplied content:")
    for key, path in paths.items():
        print(f"  {key}: {path}")


def cmd_apply(args):
    from jobauto.actions import apply_to_job

    apply_to_job(args.job_id)
    print("Marked as applied.")


def cmd_serve(args):
    import uvicorn

    db.init_db()
    uvicorn.run("jobauto.web.app:app", host="127.0.0.1", port=args.port, reload=False)


def main():
    parser = argparse.ArgumentParser(prog="jobauto")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="Initialize the local database and profile file").set_defaults(func=cmd_init)

    p = sub.add_parser("parse-resume", help="Draft your profile.yaml from an existing resume file")
    p.add_argument("file", help="Path to a .pdf, .docx, or .txt resume")
    p.set_defaults(func=cmd_parse_resume)

    p = sub.add_parser("search", help="Search configured job sources and store new listings")
    p.add_argument("--sources", help="Comma-separated source names (default: official APIs only)")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("add-job", help="Manually track a job by URL (e.g. found on Handshake, Blind, etc.)")
    p.add_argument("url")
    p.add_argument("--title", required=True)
    p.add_argument("--company", required=True)
    p.add_argument("--location", default="")
    p.add_argument("--description", default="")
    p.set_defaults(func=cmd_add_job)

    p = sub.add_parser("list", help="List stored jobs")
    p.add_argument("--status", help="Filter by status (new, generated, ready, applied, ...)")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("generate", help="Generate a tailored resume + cover letter for a job")
    p.add_argument("job_id", type=int)
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser(
        "render-manual",
        help="Render+save documents from tailored content you already have (e.g. written by a Claude Code "
        "session under your subscription instead of the metered API) - see README's 'Using your Claude "
        "subscription instead of API credits' section",
    )
    p.add_argument("job_id", type=int)
    p.add_argument("--tailored-json", required=True, help="Path to a JSON file matching the resume tailoring shape")
    p.add_argument("--cover-letter", required=True, help="Path to a plain-text cover letter file")
    p.set_defaults(func=cmd_render_manual)

    p = sub.add_parser("apply", help="Open the job application and auto-fill it (you review & submit)")
    p.add_argument("job_id", type=int)
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("serve", help="Run the local review dashboard")
    p.add_argument("--port", type=int, default=8787)
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
