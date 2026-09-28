"""Work out who will read this OPR at the promotion board: the ratee's competitive/developmental category.

Boards meet within a category (USSF: LSF for O-1-O-3 and O-6+, LSF-O / LSF-F for O-4-O-5;
USAF: LAF-A/C/F/I/N/X), so that category's officers are the audience. Their career fields' jargon reads
as familiar; other fields' jargon should be spelled out or put in plain language.

Usage:  audience.py --grade Maj --core 63A [--service USSF] [--draft draft.json --write]
"""
import argparse
import re
from pathlib import Path

from common import DATA_DIR, load_json, save_json, utf8_stdout


def grade_code(grade):
    g = grade.strip()
    if re.fullmatch(r"O-\d{1,2}", g, re.I):
        return g.upper()
    for r in load_json(DATA_DIR / "ranks.json")["officer"]:
        if g.lower() in (r["abbr"].lower(), r["name"].lower()):
            return r["grade"]
    raise ValueError(f"unknown officer grade: {grade}")


def core_code(core):
    """63A4 -> 63A, 13S3C -> 13S, 19ZXA -> 19ZXA, 11X -> 11X."""
    c = core.strip().upper()
    cats = load_json(DATA_DIR / "competitive_categories.json")
    known = set(cats["specialty_names"])
    for n in range(len(c), 1, -1):
        if c[:n] in known:
            return c[:n]
    m = re.match(r"(\d\d[A-Z])", c)
    return m.group(1) if m else c


def resolve(grade, core, service="USSF", work_dir=None):
    cats = load_json(DATA_DIR / "competitive_categories.json")
    g, spec = grade_code(grade), core_code(core)
    fam = lambda s: cats["specialty_fields"].get(s, [])  # noqa: E731
    found = None
    if service.upper() == "USSF":
        for band in cats["ussf_competitive_categories"]:
            if g in band["grades"]:
                found = next((c for c in band["categories"] if spec in c["specialties"]), None)
    else:
        found = next((c for c in cats["usaf_developmental_categories"] if spec in c["specialties"]
                      or any(spec[:2] == s[:2] and s.endswith("X") for s in c["specialties"])), None)
    if not found:
        return {"service": service, "grade": g, "core": spec, "category": None,
                "note": "category not found; ask the user which category boards them"}
    fields = sorted({f for s in found["specialties"] for f in fam(s)})
    return {"service": service.upper(), "grade": g, "core": spec, "category": found["code"],
            "category_name": found["name"], "board_specialties": found["specialties"],
            "board_specialty_names": [cats["specialty_names"].get(s, s) for s in found["specialties"]],
            "audience_fields": fields,
            "guidance": "Terms native to audience_fields may be used (still defined in Sec X if not approved). "
                        "Experience from other fields must be spelled out, generalized, or put in plain language."}


def load_terms(work_dir=None):
    terms = load_json(DATA_DIR / "career_field_terms.json")["fields"]
    if work_dir and (Path(work_dir) / "career_field_terms.json").is_file():
        for k, v in load_json(Path(work_dir) / "career_field_terms.json")["fields"].items():
            terms[k] = sorted(set(terms.get(k, [])) | set(v))
    return terms


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grade", required=True)
    ap.add_argument("--core", required=True, help="core AFSC/SFSC, e.g. 63A4")
    ap.add_argument("--service", default="USSF")
    ap.add_argument("--draft")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    board = resolve(args.grade, args.core, args.service)
    for k, v in board.items():
        print(f"{k:22} {', '.join(v) if isinstance(v, list) else v}")
    if args.draft and args.write:
        d = load_json(args.draft)
        d["board"] = board
        save_json(args.draft, d)
        print(f"stored in {args.draft} as 'board'")


if __name__ == "__main__":
    main()
