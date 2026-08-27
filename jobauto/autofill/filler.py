"""Semi-automatic application filler. Opens the job's application page in a
normal, visible browser, fills in what it confidently recognizes from your
profile, uploads your tailored resume/cover letter, and then STOPS and waits
for you to review everything and click Submit yourself. It never submits a
form on its own.
"""

import re
from pathlib import Path

from jobauto.autofill.field_map import build_text_field_values, YES_NO_FIELD_PATTERNS
from jobauto.browser import persistent_page

_APPLY_LINK_RE = re.compile(r"\bapply\b", re.I)

_CONTEXT_JS = """
el => {
  const parts = [];
  if (el.id) {
    const lbl = document.querySelector(`label[for="${el.id}"]`);
    if (lbl) parts.push(lbl.innerText);
  }
  const wrappingLabel = el.closest('label');
  if (wrappingLabel) parts.push(wrappingLabel.innerText);
  if (el.getAttribute('aria-label')) parts.push(el.getAttribute('aria-label'));
  if (el.getAttribute('placeholder')) parts.push(el.getAttribute('placeholder'));
  if (el.name) parts.push(el.name);
  if (el.id) parts.push(el.id);
  return parts.join(' | ');
}
"""


def _reveal_application_form(page):
    """Some ATS platforms (e.g. Ashby) show only a job-description page until you click
    'Apply' - the real form lives behind that click, often on a separate route entirely.
    If no form-like inputs are present yet, look for an apply link/button and click it."""
    has_form_field = page.query_selector("input[type=email], input[type=file], textarea") is not None
    if has_form_field:
        return
    candidates = list(page.get_by_role("link", name=_APPLY_LINK_RE).all()) + list(
        page.get_by_role("button", name=_APPLY_LINK_RE).all()
    )
    for candidate in candidates:
        try:
            if candidate.is_visible():
                candidate.click()
                page.wait_for_timeout(2500)
                return
        except Exception:
            continue


def fill_application(job_url: str, profile: dict, resume_path: Path, cover_letter_path: Path | None = None):
    text_values = build_text_field_values(profile)
    filled_log = []

    with persistent_page() as page:
        page.goto(job_url, wait_until="domcontentloaded")
        page.wait_for_timeout(2000)
        _reveal_application_form(page)

        # --- text / email / tel inputs + textareas ---
        for el in page.query_selector_all(
            "input[type=text], input[type=email], input[type=tel], input:not([type]), textarea"
        ):
            try:
                if not el.is_visible():
                    continue
                context = el.evaluate(_CONTEXT_JS) or ""
                current_value = el.input_value()
                if current_value:
                    continue
                for pattern, value in text_values:
                    if value and pattern.search(context):
                        el.fill(value)
                        filled_log.append((context.strip()[:60], value))
                        break
            except Exception:
                continue

        # --- file inputs (resume / cover letter uploads) ---
        for el in page.query_selector_all("input[type=file]"):
            try:
                context = (el.evaluate(_CONTEXT_JS) or "").lower()
                if "cover" in context and cover_letter_path and cover_letter_path.exists():
                    el.set_input_files(str(cover_letter_path))
                    filled_log.append((context.strip()[:60], f"uploaded {cover_letter_path.name}"))
                elif resume_path.exists():
                    el.set_input_files(str(resume_path))
                    filled_log.append((context.strip()[:60], f"uploaded {resume_path.name}"))
            except Exception:
                continue

        # --- yes/no radios and selects for work authorization / sponsorship ---
        wants_sponsorship = profile.get("personal", {}).get("willing_to_sponsor_needed", False)
        radio_groups = page.query_selector_all(
            "fieldset:has(input[type=radio]), [role=radiogroup], div:has(> input[type=radio]), "
            "div:has(> label > input[type=radio])"
        )
        for fieldset in radio_groups:
            try:
                context = fieldset.inner_text()[:300] if fieldset.is_visible() else ""
            except Exception:
                continue
            for pattern, meaning in YES_NO_FIELD_PATTERNS:
                if not pattern.search(context):
                    continue
                want_yes = (
                    True
                    if meaning == "work_authorization_positive"
                    else wants_sponsorship
                )
                target_text = "yes" if want_yes else "no"
                radios = fieldset.query_selector_all("input[type=radio]")
                for radio in radios:
                    try:
                        label_text = (radio.evaluate(_CONTEXT_JS) or "").strip().lower()
                        if label_text == target_text or label_text.startswith(target_text):
                            radio.check()
                            filled_log.append((context.strip()[:60], target_text))
                            break
                    except Exception:
                        continue

        print("\n=== JobAuto autofill summary ===")
        if filled_log:
            for label, value in filled_log:
                print(f"  [{label}] -> {value}")
        else:
            print("  Nothing could be confidently auto-filled - fill the form manually.")
        print(
            "\nReview every field carefully (especially any yes/no legal questions), "
            "then submit the application yourself in the browser window."
        )
        input("Press Enter here once you're done (this closes the browser)...\n")
