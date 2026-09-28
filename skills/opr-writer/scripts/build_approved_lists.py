"""Build approved acronym/abbreviation JSON from a command writing guide's attachments PDF.

Default input is the CFC Writing Guide Attachments (26 Jun 2026): Attachment 1 (common acronyms,
never listed/defined on evaluations) and Attachment 2 (approved abbreviations, written exactly
as listed; only -'d, -'s, -s, -es may be added; -s/-es never on abbreviated verbs).

Usage:
  python build_approved_lists.py <attachments.pdf> [--out DIR] [--source "CFC Writing Guide Attachments 26Jun2026"]
                                 [--glossary glossary.json]
"""
import argparse
import re
import sys
from pathlib import Path

from common import DATA_DIR, load_json, save_json, utf8_stdout

# Words in an Att 2 meaning that make the abbreviation verb-capable (so a -'d form is legal).
VERB_MEANINGS = {
    "achieve", "authorize", "cancel", "certify", "change", "collaborate", "coordinate",
    "deliver", "deploy", "develop", "direct", "educate", "establish", "estimate", "evacuate",
    "evaluate", "generate", "increase", "decrease", "manage", "maximize", "organize", "prepare",
    "publish", "qualify", "recommend", "regulate", "reorganize", "review", "schedule", "simulate",
    "support", "synchronize", "target", "transfer", "award", "volunteer", "certify", "simulate",
}

# Forms containing "/" that are a single abbreviation, not alternates.
SLASH_WHOLE = re.compile(r"^(?:\w/|b/w|h/w|s/w|w/in|w/o|stan/eval|.*/CC)$")

# Known glitches in the source PDF text (missing parentheses, typos).
FIXUPS = [
    (re.compile(r"^NCOY Noncommissioned"), "NCOY (Noncommissioned"),
    (re.compile(r"^op\(s\)\) "), "op(s) "),
]

REQUIRED_ACRONYMS = ["STO", "SPT", "NCOY", "FOC", "CFACC", "C4ISR", "HHQ", "MD", "SD", "USSPACECOM",
                     "BA", "DLA", "ITW/AA", "AT/FP", "JA", "SAF"]
REQUIRED_ABBREVS = ["coord", "f/", "ldrship", "kt", "kts", "Del", "DEL", "w/", "TB", "Jt", "tm", "Dir", "dir"]

ENTRY_START = re.compile(r"^(?P<short>(?:Pro Dev|1st Sgt|[^\s(]+(?:\([^\s()]*\))?))\s+\((?P<rest>.*)$")


def norm(text):
    return (text.replace("’", "'").replace("‘", "'").replace("“", '"')
            .replace("”", '"').replace("–", "-").replace("—", "--").replace(" ", " "))


def pdf_text(path):
    from pypdf import PdfReader

    return norm("\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages))


def split_attachments(text):
    """Return (acronym_lines, abbreviation_lines)."""
    lines = [ln.strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln and not re.fullmatch(r"\d+", ln)]
    # pypdf sometimes splits the first letters of an entry onto their own line ("D" / "ir (Director...").
    merged = []
    for ln in lines:
        if merged and re.fullmatch(r"[A-Za-z0-9]{1,3}", merged[-1]) and ENTRY_START.match(merged[-1] + ln):
            merged[-1] += ln
        else:
            merged.append(ln)
    lines = merged
    try:
        a1 = next(i for i, ln in enumerate(lines) if ln.upper() == "ACRONYMS")
        a2 = next(i for i, ln in enumerate(lines) if ln.upper() == "ABBREVIATIONS")
    except StopIteration:
        sys.exit("Could not find ACRONYMS / ABBREVIATIONS headings in the PDF text.")

    def body(seg):
        return [ln for ln in seg if not re.match(r"^(Attachment \d+|The following are|evaluation or|deviations are|added to|dir, and|directors or)", ln)]

    return body(lines[a1 + 1:a2]), body(lines[a2 + 1:])


def balanced(text):
    return text.count("(") <= text.count(")")


def parse_entries(lines):
    """Parse 'SHORT (meaning)' entries that may wrap lines or lack a closing parenthesis."""
    entries, cur = [], None
    for ln in lines:
        for pat, rep in FIXUPS:
            ln = pat.sub(rep, ln)
        m = ENTRY_START.match(ln)
        starts_new = bool(m) and (cur is None or balanced(cur) or _looks_like_short(m.group("short")))
        if starts_new:
            if cur:
                entries.append(cur)
            cur = ln
        elif cur is not None:
            cur += ("" if cur.endswith("-") else " ") + ln
    if cur:
        entries.append(cur)

    out = []
    for raw in entries:
        m = ENTRY_START.match(raw)
        short, rest = m.group("short"), m.group("rest")
        depth, meaning, note = 1, "", ""
        for i, ch in enumerate(rest):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    note = rest[i + 1:].strip()
                    break
            meaning += ch
        out.append({"listed": short, "meaning": re.sub(r"\s+", " ", meaning).strip(),
                    "note": note.strip("* ").strip()})
    return out


def _looks_like_short(short):
    """A wrapped continuation rarely begins with an all-caps token or a listed-style shortening."""
    return bool(re.search(r"[A-Z]{2}|/|'|\d", short)) or len(short) <= 6


def expand_forms(listed):
    """kt(s) -> kt, kts; DEL/Del -> DEL, Del; dply(mnt) -> dply, dplymnt; vol('d) -> vol, vol'd."""
    parts = [listed] if SLASH_WHOLE.match(listed) else listed.split("/")
    forms = []
    for p in parts:
        m = re.fullmatch(r"(.+?)\(([^()]+)\)", p)
        if m:
            forms += [m.group(1), m.group(1) + m.group(2)]
        else:
            forms.append(p)
    return [f for f in forms if f]


def pos_of(meaning, forms):
    words = set(re.findall(r"[a-z]+", meaning.lower()))
    if any(f.endswith("'d") or f.endswith("recd") for f in forms):
        return "verb_form"
    return "verb" if words & VERB_MEANINGS else "noun"


def build(pdf, source):
    acr_lines, abb_lines = split_attachments(pdf_text(pdf))
    acronyms, notes = {}, {}
    for e in parse_entries(acr_lines):
        parts = e["listed"].split("/")
        # USSPACECOM/USSC are alternates; ITW/AA and AT/FP are single acronyms.
        forms = parts if len(parts) > 1 and all(len(p) >= 4 for p in parts) else [e["listed"]]
        for form in forms:
            acronyms.setdefault(form, [])
            if e["meaning"] not in acronyms[form]:
                acronyms[form].append(e["meaning"])
        if e["note"]:
            notes[e["listed"]] = e["note"]

    abbrevs = []
    for e in parse_entries(abb_lines):
        forms = expand_forms(e["listed"])
        pos = pos_of(e["meaning"], forms)
        meaning, note = e["meaning"], e["note"]
        if " - " in meaning:  # "for - do not use a space after slash"
            meaning, note = meaning.split(" - ", 1)
        # -'d attaches to the verb base only, never to plural/noun expansions (kts, dplymnt).
        bases = [f for f in forms if not re.search(r"(?:mnt|s)$", f) or f == forms[0]] if pos == "verb" else []
        abbrevs.append({"listed": e["listed"], "forms": forms, "meaning": meaning.strip(), "pos": pos,
                        "d_form_allowed": pos == "verb", "d_forms": [b + "'d" for b in bases],
                        "note": note.strip()})

    common = {"source": source, "kind": "common_acronyms",
              "rule": "Commonly accepted acronyms; do not list/define these on evaluations. "
                      "Approved only for the listed meaning(s).",
              "entries": dict(sorted(acronyms.items(), key=lambda kv: kv[0].upper())), "notes": notes}
    approved = {"source": source, "kind": "approved_abbreviations",
                "rules": {
                    "exact_form": "Abbreviations must be written as listed (case-sensitive).",
                    "suffixes": ["'d", "'s", "s", "es"],
                    "no_plural_on_verbs": "-s and -es cannot be added to abbreviated verbs; allowed on abbreviated nouns.",
                    "consistency": "Once abbreviated, use the abbreviation everywhere in the evaluation.",
                    "no_space_after_slash": ["f/", "w/"]},
                "entries": abbrevs}
    return common, approved


def validate(common, approved, glossary_path=None):
    problems = []
    forms = {f for e in approved["entries"] for f in e["forms"]}
    for a in REQUIRED_ACRONYMS:
        if a not in common["entries"]:
            problems.append(f"missing acronym {a}")
    for a in REQUIRED_ABBREVS:
        if a not in forms:
            problems.append(f"missing abbreviation {a}")
    print(f"acronyms: {len(common['entries'])}  abbreviation entries: {len(approved['entries'])}  forms: {len(forms)}")
    verbs = sorted(f for e in approved["entries"] for f in e.get("d_forms", []))
    print("verb-capable (-'d allowed):", ", ".join(verbs))
    if glossary_path and Path(glossary_path).is_file():
        gl = load_json(glossary_path)["entries"]
        gl_shorts = set(gl)
        ours = set(common["entries"]) | forms
        only_gl = sorted(gl_shorts - ours)
        only_ours = sorted(ours - gl_shorts)
        print(f"glossary cross-check: {len(only_gl)} in glossary only, {len(only_ours)} in this list only")
        print("  glossary only (sample):", ", ".join(only_gl[:40]))
        print("  this list only (sample):", ", ".join(only_ours[:40]))
    return problems


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf")
    ap.add_argument("--out", default=str(DATA_DIR))
    ap.add_argument("--source", default="Built from CFC writing guidance (Writing Guide Attachments, 26 Jun 2026). "
                                         "The source document is not included.")
    ap.add_argument("--glossary", default=str(DATA_DIR / "glossary.json"))
    args = ap.parse_args()

    common, approved = build(args.pdf, args.source)
    problems = validate(common, approved, args.glossary)
    if problems:
        print("VALIDATION FAILED:\n  " + "\n  ".join(problems))
        sys.exit(1)
    save_json(Path(args.out) / "common_acronyms.json", common)
    save_json(Path(args.out) / "approved_abbreviations.json", approved)
    print(f"wrote {args.out}/common_acronyms.json and approved_abbreviations.json")


if __name__ == "__main__":
    main()
