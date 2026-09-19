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
    if result.get("filtered_out_non_us"):
        print(f"Filtered out {result['filtered_out_non_us']} non-US listings (set preferences.us_only: false to disable).")
    if result.get("filtered_out_excluded"):
        print(f"Filtered out {result['filtered_out_excluded']} listings matching preferences.keywords_exclude.")
    if result.get("filtered_out_over_experience"):
        print(f"Filtered out {result['filtered_out_over_experience']} listings requiring more experience than preferences.max_years_experience.")
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
    rows = db.list_jobs(status=args.status, max_years=args.max_years, posted_within_days=args.posted_within_days)
    try:
        for row in rows:
            years = f"~{row['estimated_min_years']}yr" if row["estimated_min_years"] is not None else "?yr"
            print(f"[{row['id']:>4}] {row['status']:<10} {years:>6} {row['title']} @ {row['company']} ({row['source']}) - {row['url']}")
        print(f"\n{len(rows)} job(s).")
    except (BrokenPipeError, OSError):
        pass  # downstream reader (e.g. `| head`) closed the pipe early


def cmd_backfill_experience(args):
    db.init_db()
    count = db.backfill_estimated_years()
    print(f"Computed estimated years-of-experience for {count} job(s) that were missing it.")


def cmd_prune_non_us(args):
    from jobauto.sources.base import is_us_location

    db.init_db()
    removed = []
    for row in db.list_jobs(status="new"):
        if not is_us_location(row["location"], bool(row["remote"])):
            removed.append(row)
            db.delete_job(row["id"])
    print(f"Removed {len(removed)} non-US job(s) with status 'new'.")
    for row in removed[:30]:
        print(f"  [{row['id']:>4}] {row['title']} @ {row['company']} - {row['location']}")
    if len(removed) > 30:
        print(f"  ... and {len(removed) - 30} more")


def cmd_prune_excluded(args):
    from jobauto.profile import load_profile
    from jobauto.sources.base import excludes_keywords

    db.init_db()
    exclude = load_profile().get("preferences", {}).get("keywords_exclude", [])
    if not exclude:
        print("preferences.keywords_exclude is empty - nothing to prune.")
        return
    removed = []
    for row in db.list_jobs(status="new"):
        if excludes_keywords(row["title"], exclude):
            removed.append(row)
            db.delete_job(row["id"])
    print(f"Removed {len(removed)} job(s) with status 'new' matching keywords_exclude {exclude}.")
    for row in removed[:30]:
        print(f"  [{row['id']:>4}] {row['title']} @ {row['company']}")
    if len(removed) > 30:
        print(f"  ... and {len(removed) - 30} more")


def cmd_prune_over_experience(args):
    from jobauto.profile import load_profile
    from jobauto.sources.experience import matches_experience_range

    db.init_db()
    max_years = load_profile().get("preferences", {}).get("max_years_experience")
    if max_years is None:
        print("preferences.max_years_experience is not set - nothing to prune.")
        return
    removed = []
    for row in db.list_jobs(status="new"):
        if not matches_experience_range(row["title"], row["description"] or "", max_years):
            removed.append(row)
            db.delete_job(row["id"])
    print(f"Removed {len(removed)} job(s) with status 'new' requiring more than {max_years} years of experience.")
    for row in removed[:30]:
        print(f"  [{row['id']:>4}] {row['title']} @ {row['company']}")
    if len(removed) > 30:
        print(f"  ... and {len(removed) - 30} more")


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

    sub.add_parser(
        "prune-non-us", help="Remove already-stored 'new' jobs whose location isn't US (retroactive cleanup)"
    ).set_defaults(func=cmd_prune_non_us)

    sub.add_parser(
        "prune-excluded", help="Remove already-stored 'new' jobs whose title matches preferences.keywords_exclude"
    ).set_defaults(func=cmd_prune_excluded)

    sub.add_parser(
        "backfill-experience", help="Compute estimated years-of-experience for jobs stored before this feature existed"
    ).set_defaults(func=cmd_backfill_experience)

    sub.add_parser(
        "prune-over-experience",
        help="Remove already-stored 'new' jobs requiring more than preferences.max_years_experience (retroactive cleanup)",
    ).set_defaults(func=cmd_prune_over_experience)

    p = sub.add_parser("list", help="List stored jobs")
    p.add_argument("--status", help="Filter by status (new, generated, ready, applied, ...)")
    p.add_argument("--max-years", type=int, help="Only show jobs estimated to need at most this many years of experience (unknown-requirement jobs are still shown)")
    p.add_argument("--posted-within-days", type=int, help="Only show jobs posted within this many days (e.g. 1, 7, 30)")
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
