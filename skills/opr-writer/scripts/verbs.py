"""Suggest opening verbs from the lexicon, excluding verbs already used as openers in a draft.

Usage:  verbs.py "saved time money" [--tier preferred] [--draft draft.json] [--max-chars 9]
Buckets (Game Changer topics) and skill categories are matched by keyword.
"""
import argparse
import re
from pathlib import Path

from common import load_json, load_verbs, normalize_spaces, utf8_stdout


def used_openers(draft_path):
    if not draft_path or not Path(draft_path).is_file():
        return set()
    draft = load_json(draft_path)
    out = set()
    for sec in draft.get("sections", {}).values():
        for line in sec.get("lines", []):
            m = re.match(r"-\s+([A-Za-z']+)", normalize_spaces(line["text"]))
            if m:
                out.add(m.group(1).lower())
    return out


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("topic", nargs="?", default="")
    ap.add_argument("--tier", default="preferred", help="preferred | neutral | overused | any")
    ap.add_argument("--draft")
    ap.add_argument("--max-chars", type=int)
    args = ap.parse_args()
    verbs = load_verbs()
    used = used_openers(args.draft)
    words = [w for w in re.findall(r"[a-z]+", args.topic.lower()) if len(w) > 2]
    rows = []
    for v in verbs:
        if args.tier != "any" and v["tier"] != args.tier:
            continue
        forms = {v["verb"].lower(), *(f.lower() for f in v["approved_forms"])}
        if forms & used or v["tier"] == "banned":
            continue
        if args.max_chars and v["chars"] > args.max_chars and not any(len(f) <= args.max_chars for f in v["approved_forms"]):
            continue
        hay = " ".join(v["buckets"] + v["skills"]).lower()
        score = sum(w in hay for w in words) if words else 1
        if score:
            rows.append((score, v))
    rows.sort(key=lambda r: (-r[0], r[1]["chars"]))
    for _, v in rows[:40]:
        forms = f" ({', '.join(v['approved_forms'])})" if v["approved_forms"] else ""
        print(f"{v['verb']}{forms}  [{v['tier']}; {', '.join(v['buckets'][:2])}]")
    if not rows:
        print("no matches; try --tier any or broader topic words")


if __name__ == "__main__":
    main()
