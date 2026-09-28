"""Split the Tongue and Quill (AFH 33-337) into small, cited chunks with an index.

Optional, local only. The skill bundles reference/tongue-and-quill-digest.md, not the full text (token cost).
Run this when a new edition appears: it builds a searchable full index outside the skill, so the digest can
be checked and updated. The PDF is ~370 pages (~200K+ tokens); nobody should ever read it whole.
Output: <out>/index.json and <out>/chunks/chNN-sMM-<slug>.txt (one per TOC section).

Usage:  build_tq_index.py "<afh33-337.pdf>" --out "<folder>/_opr_work/tq" [--compare OLD_DIR]
  --compare  diff OPR-relevant chapters (19, 25-28) against an older local build
Without an older build, compare the new chapters with the digest's page cites by hand, then update the digest.
"""
import argparse
import difflib
import re
from collections import Counter
from pathlib import Path

from common import load_json, save_json, utf8_stdout, write_text

TOC_LINE = re.compile(r"^(?P<title>.+?)\s*\.{4,}\s*(?P<page>\d+)\s*$")
FOOTER = re.compile(r"^\s*-\s*(?P<p>\d+|[ivxlc]+)\s*-\s*$", re.M)
STOP = set("""a an the and or of to in for on with by as at is are be this that it from your you not can
may will use used using when which each should must other more have has all any also into than their them
they these those its our we if do does such see page chapter""".split())
OPR_CHAPTERS = {19, 25, 26, 27, 28}
MAX_LINES = 300


def norm(s):
    return s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40]


def build(pdf, out_dir):
    from pypdf import PdfReader

    reader = PdfReader(str(pdf))
    pages = [norm(p.extract_text() or "") for p in reader.pages]
    head = "\n".join(pages[:3])
    edition = re.search(r"AFH\s*33-337,?\s*(\d{1,2}\s+[A-Z]{3,9}\s+\d{4})", head) or \
        re.search(r"AFH\s*33-337,?\s*(\d{1,2}\s+[A-Z]{3,9}\s+\d{4})", "\n".join(pages[:8]))
    change = re.search(r"Incorporating Change (\d+),?\s*(\d{1,2} \w+ \d{4})", head)

    printed_to_idx = {}
    for i, text in enumerate(pages):
        m = FOOTER.search(text)
        if m and m.group("p").isdigit():
            printed_to_idx.setdefault(int(m.group("p")), i)

    toc, chapter = [], None
    for text in pages[:15]:
        for ln in text.splitlines():
            m = TOC_LINE.match(ln.strip())
            if not m:
                continue
            title, page = m.group("title").strip(), int(m.group("page"))
            cm = re.match(r"CHAPTER (\d+):?\s*(.*)", title)
            if cm:
                chapter = (int(cm.group(1)), cm.group(2).strip())
                toc.append({"chapter": chapter[0], "chapter_title": chapter[1], "section": "(chapter opening)", "page": page})
            elif title.startswith("PART ") or chapter is None:
                continue
            else:
                toc.append({"chapter": chapter[0], "chapter_title": chapter[1], "section": title, "page": page})

    out_dir = Path(out_dir)
    chunk_dir = out_dir / "chunks"
    chunk_dir.mkdir(parents=True, exist_ok=True)
    for old in chunk_dir.glob("*.txt"):
        old.unlink()
    index = []
    last_printed = max(printed_to_idx) if printed_to_idx else len(pages)
    for n, entry in enumerate(toc):
        start = entry["page"]
        end = toc[n + 1]["page"] if n + 1 < len(toc) else last_printed
        end = max(start, end)
        idx = [printed_to_idx[p] for p in range(start, end + 1) if p in printed_to_idx]
        if not idx:
            continue
        page_texts = [(p, f"[p. {p}]\n{pages[printed_to_idx[p]]}") for p in range(start, end + 1) if p in printed_to_idx]
        # keep every chunk small (<= MAX_LINES) so a lookup never pulls a huge section
        parts, cur = [], []
        for p, t in page_texts:
            if cur and sum(x[1].count("\n") + 1 for x in cur) + t.count("\n") + 1 > MAX_LINES:
                parts.append(cur)
                cur = []
            cur.append((p, t))
        if cur:
            parts.append(cur)
        sec_no = sum(1 for e in toc[:n] if e["chapter"] == entry["chapter"])
        for k, part in enumerate(parts):
            text = "\n".join(t for _, t in part)
            suffix = f"-part{k + 1}" if len(parts) > 1 else ""
            name = f"ch{entry['chapter']:02d}-s{sec_no:02d}-{slug(entry['section'])}{suffix}.txt"
            write_text(chunk_dir / name, text)
            words = Counter(w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in STOP)
            index.append({"id": name[:-4], "chapter": entry["chapter"], "chapter_title": entry["chapter_title"],
                          "section": entry["section"] + (f" (part {k + 1}/{len(parts)})" if suffix else ""),
                          "pages": [part[0][0], part[-1][0]], "file": f"chunks/{name}",
                          "lines": text.count("\n") + 1, "opr_relevant": entry["chapter"] in OPR_CHAPTERS,
                          "keywords": [w for w, _ in words.most_common(12)]})
    meta = {"kind": "tongue_and_quill_index", "source_file": Path(pdf).name,
            "edition": edition.group(1) if edition else "unknown",
            "change": f"Change {change.group(1)}, {change.group(2)}" if change else "",
            "rule": "Never open the PDF. Read this index, then at most 2 chunk files. Cite chapter and page.",
            "chunks": index}
    save_json(out_dir / "index.json", meta)
    return meta


def compare(new_dir, old_dir):
    new, old = load_json(Path(new_dir) / "index.json"), load_json(Path(old_dir) / "index.json")
    print(f"edition {old['edition']} -> {new['edition']}")
    old_by = {(c["chapter"], c["section"]): c for c in old["chunks"]}
    for c in new["chunks"]:
        if not c["opr_relevant"]:
            continue
        o = old_by.get((c["chapter"], c["section"]))
        if not o:
            print(f"NEW SECTION ch{c['chapter']} {c['section']}")
            continue
        a = (Path(old_dir) / o["file"]).read_text(encoding="utf-8").splitlines()
        b = (Path(new_dir) / c["file"]).read_text(encoding="utf-8").splitlines()
        ratio = difflib.SequenceMatcher(None, a, b).ratio()
        if ratio < 0.98:
            print(f"CHANGED ch{c['chapter']} {c['section']} (similarity {ratio:.2f}) -> update the digest")


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--out", required=True, help="a local folder, e.g. <folder>/_opr_work/tq (never inside the skill)")
    ap.add_argument("--compare")
    args = ap.parse_args()
    meta = build(args.pdf, args.out)
    print(f"edition {meta['edition']} {meta['change']}: {len(meta['chunks'])} chunks -> {args.out}")
    if args.compare:
        compare(args.out, args.compare)


if __name__ == "__main__":
    main()
