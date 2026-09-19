# JobAuto

A personal job-search assistant for the US job market. It finds openings, drafts a
tailored resume (PDF + DOCX), CV, and cover letter for each one using Claude, and
opens/auto-fills the application form in a real browser window for you to review
and submit yourself.

**This is a semi-automatic tool, by design.** It never submits an application on
its own — it fills in what it confidently recognizes, then hands control back to
you to double check and click Submit. That protects you from a bad AI-written
application going out unreviewed, and avoids the account-ban risk that fully
autonomous "auto-apply" bots run into on sites like LinkedIn.

## How it works

1. **Your profile** (`data/profile.yaml`) is the single source of truth about your
   background — work history, skills, education, preferences. Every generated
   document is built *from* this file; the AI is only allowed to rephrase/reorder
   what's already there, never invent experience.
2. **Job sources** search for openings and store them in a local SQLite database.
3. For any job you like, **generate** a tailored resume/CV (PDF + DOCX) and cover
   letter (PDF) with one click.
4. **Apply**: opens the job's application page in a visible browser, fills in
   recognized fields and uploads your documents, then pauses for your review.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
copy .env.example .env        # then fill in your API keys
copy data\profile.example.yaml data\profile.yaml   # then fill in your real info
python -m jobauto.cli init
```

Or skip the manual profile edit and draft one from an existing resume:

```bash
python -m jobauto.cli parse-resume path\to\your_resume.pdf
```

Then **open `data/profile.yaml` and review/correct it by hand** — especially
`work_authorization`, `preferences.min_salary`, and `preferences.target_companies`
(see below).

### API keys (`.env`)

| Key | Required for | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Resume/cover letter generation, resume parsing | https://console.anthropic.com |
| `USAJOBS_API_KEY` + `USAJOBS_USER_AGENT_EMAIL` | US federal job search | https://developer.usajobs.gov/APIRequest/Index (free, instant) |
| `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` | Adzuna aggregator search | https://developer.adzuna.com/ (free tier) |

There's no persistent free tier for the Anthropic API itself - you need at least a small
paid credit balance (console.anthropic.com -> Plans & Billing) before `ANTHROPIC_API_KEY`
will work. To keep that cost minimal, the tool defaults to `claude-haiku-4-5` rather than a
larger model - tailoring a resume/cover letter is a well-defined writing task that doesn't
need top-tier reasoning, and Haiku runs it for roughly $0.01-0.02 per job instead of
$0.20-0.40. A few dollars of credit will last a very long time. If you want higher-effort
writing and don't mind the extra cost, set `CLAUDE_MODEL=claude-sonnet-5` (or `claude-opus-5`)
in `.env`.

Greenhouse, Lever, and Ashby need no key — just company board tokens (see below).

### Using a Claude.ai subscription instead of API credits

A Claude.ai Pro/Max chat subscription and the Anthropic API are billed separately - there's
no setting that lets a chat subscription authorize a script's API calls, and this tool won't
try to route around that. But if you're already running this project from inside a Claude
Code session (as opposed to a bare terminal), that session itself runs under your Claude.ai
subscription - so you can just ask it to do the tailoring directly instead of the script
calling the metered API:

1. Ask Claude Code: "tailor job `<id>` for me" (give it the job id from `jobauto list`).
2. It reads that job's real description and your `profile.yaml`, writes the tailored resume
   JSON and cover letter text itself (same no-invented-experience rules as `generation/tailor.py`),
   and saves them to two files.
3. It runs `python -m jobauto.cli render-manual <id> --tailored-json <path> --cover-letter <path>`
   to render and store the PDF/DOCX - no `ANTHROPIC_API_KEY` involved at all.

This only works inside a Claude Code session (or by pasting the same prompts into Claude.ai's
free chat yourself and saving the reply to files by hand); the plain `generate` CLI command
still needs a funded `ANTHROPIC_API_KEY` since it runs unattended, without a Claude session
to do the writing for it.

### Finding target companies (Greenhouse/Lever/Ashby)

These three run most mid-size/large tech companies' career pages and have clean,
free public APIs — but no cross-company search. Find each company's slug from its
careers page URL and add it to `preferences.target_companies` in `profile.yaml`:

| Careers URL looks like | Add slug under |
|---|---|
| `boards.greenhouse.io/stripe` | `target_companies.greenhouse: [stripe]` |
| `jobs.lever.co/netflix` | `target_companies.lever: [netflix]` |
| `jobs.ashbyhq.com/linear` | `target_companies.ashby: [linear]` |

## Usage

```bash
# Search official-API sources (fast, reliable, no ToS risk)
python -m jobauto.cli search

# Also try the experimental browser-scraper sources (see caveats below)
python -m jobauto.cli search --sources greenhouse,lever,ashby,usajobs,adzuna,indeed,linkedin,dice,ycombinator

# List what's been found
python -m jobauto.cli list

# Only show jobs estimated to need 3 years of experience or less (unknown-requirement
# jobs are still shown - see "Experience-level filtering" below)
python -m jobauto.cli list --max-years 3

# Generate tailored documents for a specific job (see its id from `list`)
python -m jobauto.cli generate 12

# Open the application, auto-fill it, review, and submit it yourself
python -m jobauto.cli apply 12

# Or use the web dashboard instead of the CLI for all of the above
python -m jobauto.cli serve
# then open http://127.0.0.1:8787
```

## US-only filtering

Companies on Greenhouse/Lever/Ashby list every office's openings on the same board - a search
against Figma or Palantir will surface London, Tel Aviv, Tokyo, Munich, etc. alongside US roles.
`preferences.us_only` in `profile.yaml` (default `true`) filters those out for `greenhouse`,
`lever`, `ashby`, and the experimental scrapers - `usajobs` and `adzuna` are already US-scoped at
the API level and aren't affected by this setting. It's a location-text heuristic (checks for a
US state, "United States"/"USA", a recognized US city, or a bare "Remote" with no other country
mentioned; rejects on any recognized non-US country/city) - not a guarantee, since it can't cover
every city name, but it removes the bulk of clearly-foreign listings. Set `us_only: false` to see
everything again.

If you already have jobs stored from before turning this on, clean them up with:

```bash
python -m jobauto.cli prune-non-us
```

This only removes jobs still at status `new` - anything you've already generated documents for
or applied to is left alone.

## Experience-level filtering

Every stored job gets an `estimated_min_years` value computed from its description (things
like "4+ years", "2-4 years of experience", "0-2 YOE", or falling back to titles like "Senior"/
"Staff"/"Manager" when no explicit number is given). This is a **non-destructive filter, not a
deletion** - unlike the US-location filter, free-text years-of-experience parsing is noisier
(a stray "our team has 40 years of combined experience" can throw it off), so nothing gets
permanently removed from the database over it. Instead:

- `python -m jobauto.cli list --max-years 3` shows only jobs estimated at <=3 years, plus any
  job where no requirement could be detected at all (so postings that just don't state a number
  aren't hidden by mistake).
- The web dashboard has the same "Max years of experience" filter box, and shows the estimate
  in an "Est. Yrs" column so you can see why something did or didn't pass.
- Jobs stored before this feature existed need one backfill: `python -m jobauto.cli backfill-experience`.

Adjust or drop the filter anytime by changing the number or clearing the box - no data is lost
either way.

## Job sources

**Official APIs (recommended, no ToS risk):** `greenhouse`, `lever`, `ashby`
(need target company slugs), `usajobs` (federal jobs), `adzuna` (aggregator).

**Experimental browser scrapers (use at your own discretion):** `indeed`,
`linkedin`, `dice`, `ycombinator`. These sites have no free public search API, so
these modules open a normal, *visible* browser and read whatever is rendered on
the public search page — no headless scraping, no stealth/anti-detection tricks,
no automated login. Two things to know:

- Their HTML changes often, so these will silently return fewer/zero results
  when a site redesigns its markup — treat them as bonus coverage, not a
  dependable source.
- **LinkedIn explicitly prohibits automated scraping in its User Agreement** and
  can restrict accounts that trigger its bot detection, even for light,
  human-paced browsing. The `linkedin` source asks you to log in manually rather
  than automating that step, but the underlying activity is still against their
  terms — this is included because it was requested, not because it's risk-free.
  If you'd rather not risk your LinkedIn account, just omit it from `--sources`.

**Not included:** Handshake requires university SSO credentials that can't be
generalized across schools, and Blind is a discussion forum rather than a
structured job board — neither has a workable path to automate here. Instead,
track listings from either (or anywhere else) with:

```bash
python -m jobauto.cli add-job "https://..." --title "Software Engineer" --company "Acme" --location "Remote"
```

or the "Add a job manually" form in the web dashboard. Once added, it gets the
same tailored-document generation and auto-fill treatment as any other job.

## Notes on the auto-fill step

The filler recognizes common field patterns (name, email, phone, LinkedIn,
location, resume/cover-letter upload, and a couple of common yes/no questions
like work authorization) across Greenhouse/Lever/Ashby/Workday-style forms. It
is heuristic, not guaranteed — **always read every field before submitting**,
especially any legal/eligibility questions. It will never click Submit for you.

## Project layout

```
jobauto/
  config.py, db.py, profile.py, profile_parser.py, claude_client.py
  sources/        job-source connectors (official APIs + experimental scrapers)
  generation/     Claude-based tailoring + PDF/DOCX rendering
  autofill/       Playwright-based semi-automatic form filler
  web/            FastAPI review dashboard
  cli.py          command-line entry point
data/
  profile.example.yaml   copy to profile.yaml and fill in
  generated/              tailored resumes/cover letters land here (gitignored)
```
