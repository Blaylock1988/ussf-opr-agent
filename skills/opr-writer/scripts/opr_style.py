"""Derive a style profile from prior OPR lines (_opr_work/history.json -> style_profile.json).

The profile tells drafting which *approved* forms and habits to imitate. It never re-introduces
unapproved shorthand: history forms that fail the approval check are reported with replacements.

Usage:  opr_style.py "<folder>/_opr_work" [--first-name Mike]
"""
import argparse
import re
from collections import Counter
from pathlib import Path

from common import load_json, normalize_spaces, save_json, utf8_stdout
from rules import Approvals, is_acronym, numbers_in, tokens


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work_dir")
    ap.add_argument("--first-name")
    args = ap.parse_args()
    work = Path(args.work_dir)
    hist = [h for h in load_json(work / "history.json")["lines"] if h["section"] != "acronyms"]
    if not hist:
        print("no history lines; defaults apply")
        save_json(work / "style_profile.json", {"has_history": False})
        return
    approvals = Approvals(work)
    perf = [h for h in hist if h["section"] in ("rater", "additional_rater", "reviewer")]
    strat = [h for h in perf if normalize_spaces(h["text"])[2:].startswith("#")]
    body = [h for h in perf if h not in strat]

    approved_use, unapproved = Counter(), {}
    for h in hist:
        text = normalize_spaces(h["text"])
        for n, (tok, _) in enumerate(tokens(text[2:])):
            if is_acronym(tok):
                continue
            for part in (tok.split("-") if "-" in tok else [tok]):
                st, detail = approvals.abbreviation_status(part, line_start=n == 0)
                if st == "approved":
                    approved_use[part] += 1
                elif st == "error":
                    unapproved.setdefault(part, detail)

    openers = Counter()
    for h in body:
        m = re.match(r"-\s+(\S+)", normalize_spaces(h["text"]))
        if m:
            openers[m.group(1)] += 1

    def share(pred, rows):
        return round(sum(1 for h in rows if pred(normalize_spaces(h["text"]))) / max(len(rows), 1), 2)

    pushes = [normalize_spaces(h["text"]).split("--", 1)[1] for h in strat if "--" in h["text"]]
    profile = {
        "has_history": True,
        "years": sorted({h["year"] for h in hist if h["year"]}),
        "lines_analyzed": len(hist),
        "separators": {"semicolon": share(lambda t: ";" in t, body), "double_dash": share(lambda t: "--" in t, body),
                       "slash_chaining": share(lambda t: re.search(r"[a-z]'?d?/[a-z]", t) is not None, body)},
        "exclamation_share": share(lambda t: "!" in t, perf),
        "first_name_in_strat": bool(args.first_name) and any(args.first_name in h["text"] for h in strat),
        "avg_numbers_per_line": round(sum(len(numbers_in(normalize_spaces(h["text"]))) for h in body) / max(len(body), 1), 2),
        "preferred_approved_forms": [f for f, _ in approved_use.most_common(40)],
        "unapproved_history_forms": unapproved,
        "openers_used_before": [w for w, _ in openers.most_common()],
        "strat_lines": [normalize_spaces(h["text"]) for h in strat],
        "push_trend": pushes,
        "note": "Imitate separators/habits and preferred approved forms only. Never reuse unapproved_history_forms; "
                "avoid repeating openers_used_before where a fresh verb works.",
    }
    save_json(work / "style_profile.json", profile)
    print(f"style profile: {len(hist)} lines, years {', '.join(profile['years'])}")
    print(f"separators {profile['separators']}, exclamation share {profile['exclamation_share']}, "
          f"avg numbers/line {profile['avg_numbers_per_line']}")
    if unapproved:
        print("history shorthand NOT to reuse:")
        for k, v in sorted(unapproved.items()):
            print(f"  {k}: {v}")
    print("recent pushes:", " | ".join(pushes[:4]))


if __name__ == "__main__":
    main()
