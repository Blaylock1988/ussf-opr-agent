"""Report how current the bundled policy data is, and warn about anything due for review.

Forms, approved acronyms, competitive categories, USSF structure, CSO priorities and board priorities
all change over time (and with each administration). Run this at setup; stale data is a warning, not a
blocker - tell the user what to refresh and where.

Usage:  data_check.py [--report-thru 2026-05-31] [--work "<folder>/_opr_work"]
"""
import argparse
from datetime import date
from pathlib import Path

from common import DATA_DIR, INSTALL_MANIFEST, SKILL_DIR, load_json, skill_hash, utf8_stdout


def install_check():
    """An installed copy doesn't follow repo edits; say so when the repo it came from has changed since."""
    mine = skill_hash()
    manifest = SKILL_DIR / INSTALL_MANIFEST
    if not manifest.is_file():
        print(f"skill {mine} (running from {SKILL_DIR}; not an install.py copy)\n")
        return
    info = load_json(manifest)
    src = Path(info.get("source", ""))
    if mine != info.get("hash"):
        print(f"WARNING: this installed copy was modified after install ({SKILL_DIR}).")
    if (src / "SKILL.md").is_file() and skill_hash(src) != mine:
        print(f"STALE INSTALL: {SKILL_DIR} differs from the repository at {src}.\n"
              f"  Tell the user to run: python install.py update   (from the repository root)\n")
    else:
        print(f"skill {mine} (installed {info.get('installed', '?')} from {src})\n")


def parse(d):
    parts = [int(x) for x in str(d).split("-")] + [1, 1]
    return date(parts[0], parts[1], parts[2])


def months_between(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month)


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report-thru", help="reporting period end date (YYYY-MM-DD)")
    ap.add_argument("--work")
    ap.add_argument("--today", default=date.today().isoformat())
    args = ap.parse_args()
    today = parse(args.today)
    install_check()
    reg =load_json(DATA_DIR / "currency.json")
    overrides = {}
    if args.work:
        w = Path(args.work)
        for name in ("approved/common_acronyms.json", "approved/approved_abbreviations.json", "form.json",
                     "board_priorities.json", "career_field_terms.json", "ussf_structure.json", "buzzwords.json"):
            if (w / name).is_file():
                overrides[name] = True
    stale = 0
    print(f"{'dataset':24} {'published':11} {'verified':9} {'age':>5}  status")
    for d in reg["datasets"]:
        verified = parse(d["verified"])
        age = months_between(verified, today)
        flags = []
        if age > d["review_months"]:
            flags.append(f"not verified in {d['review_months']} mo")
        if args.report_thru and months_between(verified, parse(args.report_thru)) > d["review_months"]:
            flags.append("last verified long before this report's period")
        status = "STALE: " + "; ".join(flags) if flags else "ok"
        stale += bool(flags)
        print(f"{d['id']:24} {d['published']:11} {d['verified']:9} {age:>4}m  {status}")
        if flags:
            print(f"{'':24}   source:  {d['source']}\n{'':24}   refresh: {d['refresh']}")
    if overrides:
        print("\nuser overrides present in _opr_work: " + ", ".join(overrides))
    print(f"\n{stale} dataset(s) need review." if stale else "\nall datasets within their review windows.")
    print("Reminder: " + reg["principle"])


if __name__ == "__main__":
    main()
