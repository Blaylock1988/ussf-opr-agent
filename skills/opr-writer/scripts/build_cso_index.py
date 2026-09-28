"""Index a CSO "Selected Works" compilation (speeches, C-Notes, articles, milestones) for impact research.

Optional, local only. The skill bundles reference/data/cso_digest.json (themes and short quotes), not the
full text (token cost). Run this on a new compilation to build a searchable full index outside the skill,
then add digest entries for anything new; it lists C-Notes missing from the digest.
Output (same schema as the Tongue and Quill index, so ref_lookup.py --dir can search it):
  <out>/index.json, <out>/chunks/<kind>-NN-<slug>.txt

Usage:  build_cso_index.py "<CSO Selected Works.pdf>" --out "<folder>/_opr_work/cso" [--cso "Gen B. Chance Saltzman"]
"""
import argparse
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

from common import DATA_DIR, load_json, save_json, utf8_stdout, write_text

TOC_LINE = re.compile(r"^(?P<title>.+?)\s*\.{4,}[\s.]*(?P<page>\d+)?\s*$")
KINDS = {"Speeches": 1, "C-Notes": 2, "Published Articles": 3, "Appendices": 4}
STOP = set("the and for that with this our are from have will you they their what not but all can more was".split())
MAX_LINES = 300


def norm(s):
    return (s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
            .replace("–", "-").replace("—", "-").replace("�", "-"))


def key(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def parse_toc(pages):
    """Return [(kind, title, printed_page)] from the table of contents."""
    lines = []
    for p in pages[:6]:
        lines += [norm(ln).strip() for ln in p.splitlines()]
    entries, kind, carry = [], None, ""
    for ln in lines:
        if ln in KINDS:
            kind = ln
            continue
        if not kind or not ln or re.fullmatch(r"[ivx]+", ln):
            continue
        m = TOC_LINE.match(carry + " " + ln if carry else ln)
        if m and "...." in ln:
            entries.append((kind, re.sub(r"\s+", " ", m.group("title")).strip(" -"), int(m.group("page") or 0)))
            carry = ""
        else:
            carry = (carry + " " + ln).strip() if carry else ln
            carry = carry.replace("Contr ol", "Control")
    return entries


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True, help="a local folder, e.g. <folder>/_opr_work/cso (never inside the skill)")
    ap.add_argument("--cso", default="Gen B. Chance Saltzman")
    args = ap.parse_args()
    from pypdf import PdfReader

    pages = [norm(p.extract_text() or "") for p in PdfReader(args.pdf).pages]
    toc = parse_toc(pages)
    body_start = next(i for i, p in enumerate(pages) if re.match(r"\s*1\s*\n", p))
    # Flatten body with printed-page markers.
    body_lines = []
    for p in pages[body_start:]:
        lines = p.splitlines()
        num = next((ln.strip() for ln in lines[:2] if ln.strip().isdigit()), None)
        if num:
            body_lines.append(f"[p. {num}]")
        body_lines += [ln for ln in lines if ln.strip() != num]

    # Locate each TOC title in the body (in order).
    positions, cursor = [], 0
    keys = [key(ln) for ln in body_lines]
    for kind, title, page in toc:
        want = key(title)[:40]
        found = None
        for i in range(cursor, len(body_lines)):
            joined = keys[i] + (keys[i + 1] if i + 1 < len(keys) else "")
            if joined.startswith(want[:25]) and want[:25]:
                found = i
                break
        if found is None:
            print(f"WARN: heading not found: {title}")
            continue
        positions.append((found, kind, title, page))
        cursor = found + 1

    out = Path(args.out)
    (out / "chunks").mkdir(parents=True, exist_ok=True)
    for old in (out / "chunks").glob("*.txt"):
        old.unlink()
    index, cnotes = [], []
    for n, (start, kind, title, page) in enumerate(positions):
        end = positions[n + 1][0] if n + 1 < len(positions) else len(body_lines)
        seg = body_lines[start:end]
        parts = [seg[i:i + MAX_LINES] for i in range(0, len(seg), MAX_LINES)] or [seg]
        for k, part in enumerate(parts):
            suffix = f"-part{k + 1}" if len(parts) > 1 else ""
            name = f"{slug(kind)}-{n:03d}-{slug(title)}{suffix}.txt"
            text = "\n".join(part)
            write_text(out / "chunks" / name, text)
            words = Counter(w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP)
            index.append({"id": name[:-4], "chapter": KINDS[kind], "chapter_title": kind, "section": title,
                          "pages": [page, page], "file": f"chunks/{name}", "lines": len(part),
                          "keywords": [w for w, _ in words.most_common(12)]})
        m = re.match(r"C.?Note\s*#\s*(\d+)\s*-\s*(.+?),\s*(\d{1,2} \w+ \d{4})$", title)
        if kind == "C-Notes" and m:
            try:
                date = datetime.strptime(m.group(3), "%d %B %Y").strftime("%Y-%m-%d")
            except ValueError:
                date = m.group(3)
            cnotes.append({"n": int(m.group(1)), "date": date, "title": m.group(2).strip(), "file": f"chunks/{name}"})
    save_json(out / "index.json", {"kind": "cso_selected_works", "source_file": Path(args.pdf).name, "edition": args.cso,
                                   "change": "", "rule": "Search with ref_lookup.py --dir; read at most 2 chunks.",
                                   "chunks": index})
    print(f"{len(index)} chunks ({len(positions)}/{len(toc)} headings found); {len(cnotes)} C-Notes -> {out}")

    have = {e["n"] for e in load_json(DATA_DIR / "cso_digest.json")["entries"] if e["type"] == "cnote"}
    for c in cnotes:
        if c["n"] not in have:
            print(f"NOT IN DIGEST: C-Note #{c['n']} {c['title']} ({c['date']}) [{c['file']}] -> add a cso_digest.json entry")


if __name__ == "__main__":
    main()
