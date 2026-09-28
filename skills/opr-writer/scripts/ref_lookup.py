"""Capped keyword lookup over the bundled reference digests. Prints at most --max-lines lines (default 80).

Sources:  tq  = reference/tongue-and-quill-digest.md (OPR-relevant T&Q rules, with page cites)
          cso = reference/data/cso_digest.json (CSO C-Notes, speeches and articles: themes and short quotes)

The full texts are not bundled, to keep token costs low. A user with a newer T&Q can build a full local
index (build_tq_index.py --out "<folder>/_opr_work/tq") and search it with --dir.

Usage:  ref_lookup.py "ordinal numbers unit designation" [--source tq]
        ref_lookup.py "space control competitive endurance" --source cso [--type cnote|speech|article]
        ref_lookup.py "hyphen compound" --dir "<folder>/_opr_work/tq" [--chapter 25]
"""
import argparse
import math
import re
from pathlib import Path

from common import DATA_DIR, REFERENCE_DIR, load_json, utf8_stdout

WINDOW = 6


def terms_of(query):
    return re.findall(r"[a-z0-9']{2,}", query.lower())


def score(text, terms, bonus_text=""):
    low, bonus = text.lower(), bonus_text.lower()
    return sum(low.count(t) for t in terms) + 5 * sum(t in bonus for t in terms)


def lookup_tq(terms, max_lines):
    text = (REFERENCE_DIR / "tongue-and-quill-digest.md").read_text(encoding="utf-8")
    sections = re.split(r"(?m)^(?=## )", text)[1:]
    # rarer terms weigh more, so "ordinal numbers" finds the ordinal rule rather than every section on numbers
    weight = {t: math.log((len(sections) + 1) / (1 + sum(t in s.lower() for s in sections))) + 0.1 for t in terms}

    def sec_score(s):
        low, head = s.lower(), s.splitlines()[0].lower()
        return sum(weight[t] * (low.count(t) + 5 * (t in head)) for t in terms)
    ranked = sorted(((sec_score(s), s) for s in sections), key=lambda x: -x[0])
    out = []
    for sc, sec in ranked[:3]:
        if not sc:
            break
        lines = sec.rstrip().splitlines()
        head, body = lines[0], lines[1:]
        hits = [i for i, ln in enumerate(body) if any(t in ln.lower() for t in terms)] or [0]
        keep = sorted({j for i in hits for j in range(i - 1, i + 2) if 0 <= j < len(body)})
        out += ["", head] + [body[j] for j in keep]
    return out


def lookup_cso(terms, max_lines, kind):
    digest = load_json(DATA_DIR / "cso_digest.json")
    ranked = []
    for e in digest["entries"]:
        if kind and e["type"] != kind:
            continue
        hay = " ".join(e.get("themes", []) + [q["text"] for q in e.get("quotes", [])] + [e.get("summary", "")])
        bonus = " ".join([e["title"]] + e.get("keywords", []))
        sc = score(hay, terms, bonus)
        phrase = " ".join(terms)
        if sc and len(terms) > 1 and phrase in bonus.lower():
            sc += 20  # the whole phrase in the title or keywords beats scattered word hits
        if sc:
            ranked.append((sc, e))
    ranked.sort(key=lambda x: -x[0])
    out = []
    for _, e in ranked[:5]:
        label = f"C-Note #{e['n']}" if e["type"] == "cnote" else e["type"].capitalize()
        out += ["", f"{label}: {e['title']} ({e.get('date') or 'undated'})" + (f"  {e['url']}" if e.get("url") else "")]
        out += [f"  theme: {t}" for t in e.get("themes", [])]
        out += [f"  quote (p. {q['page']}): \"{q['text']}\"" for q in e.get("quotes", [])]
    return out


def lookup_index(terms, max_lines, index_dir, chapter):
    """Search a locally built full index (build_tq_index.py / build_cso_index.py output)."""
    index = load_json(Path(index_dir) / "index.json")
    scored = []
    for c in index["chunks"]:
        if chapter and c["chapter"] != chapter:
            continue
        lines = (Path(index_dir) / c["file"]).read_text(encoding="utf-8").splitlines()
        hits = [i for i, ln in enumerate(lines) if any(t in ln.lower() for t in terms)]
        if hits:
            scored.append((score("\n".join(lines), terms, c["section"]), c, lines, hits))
    scored.sort(key=lambda x: -x[0])
    out = [f"{index['kind']} ({index['edition']} {index.get('change', '')})"]
    for _, c, lines, hits in scored[:3]:
        best = max(hits, key=lambda h: sum(1 for x in hits if abs(x - h) <= WINDOW))
        lo, hi = max(0, best - WINDOW), min(len(lines), best + WINDOW + 1)
        page = next((m.group(1) for ln in reversed(lines[:lo + 1]) for m in [re.match(r"\[p\. (\d+)\]", ln)] if m), c["pages"][0])
        out += ["", f"--- ch {c['chapter']} ({c['chapter_title']}) / {c['section']} / p. {page} [{c['file']}]"] + lines[lo:hi]
    return out


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("query")
    ap.add_argument("--source", choices=["tq", "cso"], default="tq")
    ap.add_argument("--type", choices=["cnote", "speech", "article"], help="cso: limit to one kind")
    ap.add_argument("--dir", help="search a locally built full index instead of the digest")
    ap.add_argument("--chapter", type=int, help="with --dir: limit to one chapter")
    ap.add_argument("--max-lines", type=int, default=80)
    args = ap.parse_args()
    terms = terms_of(args.query)
    if args.dir:
        out = lookup_index(terms, args.max_lines, args.dir, args.chapter)
    elif args.source == "tq":
        out = lookup_tq(terms, args.max_lines)
    else:
        out = lookup_cso(terms, args.max_lines, args.type)
    print(f"{args.source if not args.dir else 'index'} - query: {args.query}")
    body = [ln for ln in out if ln is not None][:args.max_lines]
    print("\n".join(body) if any(ln.strip() for ln in body) else "no matches; try other terms")


if __name__ == "__main__":
    main()
