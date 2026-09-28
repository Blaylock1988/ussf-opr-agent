"""Build the Sec X (Remarks) acronym string for a draft.

Rules: list only acronyms that are NOT approved for the meaning used (CFC Att 1 / AFPC / user list);
never list abbreviations; every listed acronym must appear in the report; sort alphabetically by
acronym; "Spelled Out (ACR); Next (ACR)" with one space after each semicolon.

Usage:  opr_acronyms.py draft.json [--write]
"""
import argparse
import sys
from pathlib import Path

from common import iter_lines, load_form, load_json, normalize_spaces, save_json, utf8_stdout
from rules import Approvals, acronym_core, is_acronym, tokens


def used_acronyms(draft, form):
    """Acronym -> list of 'section[line]' where it appears (duty title included)."""
    found = {}
    proper = " ".join(draft.get("proper_nouns", []))
    texts = [("duty_title", draft.get("sections", {}).get("job_description", {}).get("duty_title", ""))]
    texts += [(f"{k}[{i + 1}]", line["text"]) for k, i, line in iter_lines(draft, form)]
    for where, text in texts:
        for tok, _ in tokens(normalize_spaces(text or "")):
            if is_acronym(tok) and tok not in proper.split():
                found.setdefault(acronym_core(tok), []).append(where)
    return found


def build_remarks(draft, form, approvals):
    """Return (remarks_string, needs_definition_without_meaning, statuses)."""
    declared = draft.get("acronyms", {})
    categories = draft.get("acronym_categories", {})
    define_categories = draft.get("settings", {}).get("define_category_acronyms", True)
    listed, missing, statuses = [], [], {}
    for acr in used_acronyms(draft, form):
        status, detail = approvals.acronym_status(acr, declared.get(acr), categories.get(acr))
        statuses[acr] = (status, detail)
        if status == "needs_definition" or (status == "category" and define_categories and declared.get(acr)):
            if declared.get(acr):
                listed.append((acr, declared[acr]))
            else:
                missing.append((acr, detail))
    listed.sort(key=lambda kv: kv[0].upper())
    return "; ".join(f"{meaning} ({acr})" for acr, meaning in listed), missing, statuses


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("draft")
    ap.add_argument("--write", action="store_true", help="store the string in draft['remarks']")
    args = ap.parse_args()
    path = Path(args.draft)
    draft = load_json(path)
    form = load_form(draft.get("form"), path.parent)
    remarks, missing, statuses = build_remarks(draft, form, Approvals(path.parent))
    print("SEC X REMARKS:\n" + (remarks or "(none required)"))
    judgment = sorted(a for a, (s, _) in statuses.items() if s == "media")
    if judgment:
        print("\nJudgment (widely known, not listed): " + ", ".join(judgment))
    if missing:
        print("\nNEED A MEANING in draft['acronyms'] before they can be listed:")
        for acr, hint in missing:
            print(f"  {acr}: {hint}")
    if args.write:
        draft["remarks"] = remarks
        save_json(path, draft)
    sys.exit(1 if missing else 0)


if __name__ == "__main__":
    main()
