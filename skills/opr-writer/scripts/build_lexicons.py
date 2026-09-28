"""Build the reference glossary and action-verb lexicon from spreadsheets.

  glossary.json      decoder only (never an approval list): short form -> meanings
  action_verbs.json  verb lexicon with topic buckets, tiers, and approved/unapproved -'d forms

Usage:
  python build_lexicons.py --glossary-xlsx "<acronym and abbreviation list.xlsx>" \
                           --verbs-xlsx "<verbs by skill.xlsx>" --verbs-xlsx "<verbs by topic.xlsx>" \
                           [--out DIR]
The source spreadsheets stay outside the repo; only the lists built from them are bundled.
Any extra glossary files (xlsx/csv with Long/Short columns) can be passed with more --glossary-xlsx.
"""
import argparse
import csv
import re
from pathlib import Path

from common import DATA_DIR, load_json, save_json, save_verbs, utf8_stdout

IRREGULAR_PAST = {
    "Led", "Built", "Drove", "Won", "Wrote", "Ran", "Sought", "Taught", "Undertook", "Withdrew",
    "Overcame", "Beat", "Bought", "Began", "Drew", "Cut", "Set", "Held", "Brought", "Spoke",
    "Troubleshot", "Chose", "Oversaw", "Rewrote", "Upheld", "Struck", "Stood-up", "Fought",
    "Taught", "Swept", "Sold", "Met", "Made", "Kept", "Found", "Gave", "Grew", "Rebuilt", "Won",
}

PREFERRED = """Forged Cemented Bolstered Fortified Revitalized Overhauled Pioneered Steered Navigated Averted
Thwarted Salvaged Slashed Brokered Synchronized Centralized Standardized Streamlined Modernized Engineered
Authored Crafted Defended Mitigated Restructured Consolidated Unified Groomed Propelled Accelerated Garnered
Netted Captured Charted Devised Fielded Mobilized Bridged Secured Negotiated Integrated Galvanized Architected
Codified Transformed Revamped Retooled Rebuilt Reshaped Solidified Safeguarded Shielded Rescued Recovered
Launched Instituted Established Formalized Automated Optimized Expedited Sharpened Honed Delivered Sustained
Advocated Championed Cultivated Mentored Coached Energized Inspired Rallied Unlocked Harnessed Leveraged
Deployed Activated Fused Orchestrated Aligned Reconciled Audited Budgeted Forecasted Allocated Programmed
Validated Certified Qualified Resolved Diagnosed Rectified Restored Upgraded Fielded Transitioned Absorbed
Onboarded Merged Molded Shaped Spurred Catalyzed Ignited Sparked Surged Amplified Boosted Expanded Extended
Doubled Tripled Multiplied Outpaced Surpassed Exceeded Anchored Arbitrated Mediated Liaised Partnered
Synced Briefed Educated Trained Drafted Rewrote Refined Crafted""".split()

OVERUSED = "Led Spearheaded Orchestrated Championed Managed Directed Drove Oversaw Executed Coordinated Supported Ensured Provided".split()

BANNED = """Quarterbacked QB'd Helped Assisted Participated Attended Utilized Used Performed Worked Handled
Zapped Dazzled Smashed Crushed Obliterated Tamed Greased Bombarded Captivated Dramatized Nailed Trumped
Liberated Xeroxed Zipped Zoomed Speaked Comforted Nursed Tended Visited Viewed Witnessed Listened Read
Learned Tried Aspired Endured Endeavored Moved Greeted Hailed Nurtured Caused Changed Did Got""".split()


def rows_from_xlsx(path, sheet=None):
    from openpyxl import load_workbook

    wb = load_workbook(path, read_only=True, data_only=True)
    sheets = [wb[sheet]] if sheet else wb.worksheets
    for ws in sheets:
        for row in ws.iter_rows(values_only=True):
            yield ws.title, [("" if v is None else str(v)).strip() for v in row]


def norm(s):
    return s.replace("’", "'").replace("‘", "'").strip()


# ---------------------------------------------------------------- glossary

def derive_type(short):
    """The source spreadsheet's Type column is unreliable (labels appear swapped); derive it."""
    letters = re.sub(r"[^A-Za-z]", "", short)
    if "'" in short or (letters and letters == letters.lower()):
        return "abbreviation"
    return "acronym"


def build_glossary(paths):
    entries = {}
    for path in paths:
        path = Path(path)
        if path.suffix.lower() == ".csv":
            with open(path, encoding="utf-8-sig") as f:
                rows = [("csv", [c.strip() for c in r]) for r in csv.reader(f)]
        else:
            rows = list(rows_from_xlsx(path))
        header = [h.lower() for h in rows[0][1]]
        li, si = header.index("long"), header.index("short")
        src_i = header.index("source") if "source" in header else None
        for _, r in rows[1:]:
            if len(r) <= max(li, si) or not r[si] or not r[li]:
                continue
            short, long_ = norm(r[si]), norm(r[li])
            meaning = {"long": long_, "type": derive_type(short),
                       "source": (r[src_i] if src_i is not None else path.stem)}
            bucket = entries.setdefault(short, [])
            if all(m["long"].lower() != long_.lower() for m in bucket):
                bucket.append(meaning)
    return {"kind": "glossary",
            "rule": "DECODER ONLY. Use to understand inputs and advise users. Never use to decide whether "
                    "a term is approved for an OPR; approval comes from the command guide / AFPC / user lists.",
            "source": "Built from a compiled list of SpOC and USAF acronyms and abbreviations seen in guidance. "
                      "The source file is not included.",
            "entries": dict(sorted(entries.items(), key=lambda kv: kv[0].upper()))}


# ---------------------------------------------------------------- verbs

def is_past_verb(w):
    return bool(re.fullmatch(r"[A-Z][a-z]+(?:-[a-z]+)?", w)) and (w.endswith("ed") or w in IRREGULAR_PAST)


def approved_d_bases():
    """Map of base abbreviation -> True when a -'d form is legal (from approved_abbreviations.json)."""
    path = DATA_DIR / "approved_abbreviations.json"
    if not path.is_file():
        return set(), set()
    ab = load_json(path)
    bases = {d[:-2].lower() for e in ab["entries"] for d in e.get("d_forms", [])}
    listed_d = {f.lower() for e in ab["entries"] if e["pos"] == "verb_form" for f in e["forms"]}
    return bases, listed_d


def past_tense(word):
    irregular = {"transfer": "transferred", "cancel": "canceled", "target": "targeted"}
    if word in irregular:
        return irregular[word]
    if word.endswith("e"):
        return word + "d"
    if re.search(r"[^aeiou]y$", word):
        return word[:-1] + "ied"
    return word + "ed"


def approved_forms_by_verb():
    """Past-tense verb -> approved short forms, derived from the approved list's meanings.

    e.g. coord (coordinate) -> Coordinated: coord'd; ID'd/Id'd (identified) -> Identified: ID'd, Id'd.
    """
    path = DATA_DIR / "approved_abbreviations.json"
    if not path.is_file():
        return {}
    out = {}
    for e in load_json(path)["entries"]:
        meaning = e["meaning"].lower().replace("(", "").replace(")", "")  # volunteer(ed) -> volunteered
        words = re.findall(r"[a-z]+", meaning)
        if e["pos"] == "verb_form":
            past = [w for w in words if w.endswith("ed")] or [past_tense(w) for w in words]
            for p in past:
                out.setdefault(p.capitalize(), []).extend(f for f in e["forms"] if f.endswith("'d") or f.endswith("recd"))
        for d in e.get("d_forms", []):
            for w in words:
                out.setdefault(past_tense(w).capitalize(), []).append(d)
    return {k: sorted(set(v)) for k, v in out.items()}


def build_verbs(paths):
    verbs = {}

    def add(word, bucket=None, skill=None):
        word = norm(word).capitalize() if word else ""
        if not is_past_verb(word):
            return None
        v = verbs.setdefault(word, {"verb": word, "buckets": set(), "skills": set(), "abbrev_forms": set()})
        if bucket:
            v["buckets"].add(bucket)
        if skill:
            v["skills"].add(skill)
        return v

    for path in paths:
        name = Path(path).name.lower()
        if "game" in name:
            # "Sheet2": header row = topic buckets, columns = verbs.
            rows = list(rows_from_xlsx(path, "Sheet2"))
            topics = rows[0][1]
            for _, r in rows[1:]:
                for i, cell in enumerate(r):
                    if cell and i < len(topics) and topics[i]:
                        add(cell.title(), bucket=topics[i].strip())
            # "Action Verbs": verbs with abbreviated forms immediately after (e.g. Coordinated | Coord'd).
            prev = None
            for _, r in rows_from_xlsx(path, "Action Verbs"):
                for cell in r:
                    cell = norm(cell)
                    if not cell:
                        continue
                    if prev and ("'" in cell or (len(cell) <= 5 and cell.lower() != prev["verb"].lower())) \
                            and cell[:2].lower() == prev["verb"][:2].lower():
                        prev["abbrev_forms"].add(cell.lower())
                        continue
                    prev = add(cell) or prev
        else:
            for sheet, r in rows_from_xlsx(path):
                for cell in r:
                    add(cell, skill=sheet.strip())

    bases, listed_d = approved_d_bases()
    tiers = {w: "preferred" for w in PREFERRED}
    tiers.update({w: "overused" for w in OVERUSED})
    tiers.update({w: "banned" for w in BANNED})
    for w in PREFERRED + OVERUSED:
        verbs.setdefault(w, {"verb": w, "buckets": set(), "skills": set(), "abbrev_forms": set()})

    for w in BANNED:
        if is_past_verb(w):
            verbs.setdefault(w, {"verb": w, "buckets": set(), "skills": set(), "abbrev_forms": set()})
    by_verb = approved_forms_by_verb()
    # A derived -'d form that collides with an explicitly listed contraction of another meaning is ambiguous
    # (rec'd is listed as "received", so it cannot also mean "recommended").
    listed_owner = {f.lower(): verb for verb, fs in by_verb.items() for f in fs if f.lower() in listed_d}
    out = []
    for w, v in sorted(verbs.items()):
        ok = [f for f in by_verb.get(w, []) if listed_owner.get(f.lower(), w) == w]
        ok_lower = {f.lower() for f in ok}
        forms = sorted(f for f in v["abbrev_forms"] if f.lower() not in ok_lower)
        out.append({"verb": w, "tier": tiers.get(w, "neutral"), "chars": len(w),
                    "buckets": sorted(v["buckets"]), "skills": sorted(v["skills"]),
                    "approved_forms": ok, "unapproved_forms": forms})
    return {"kind": "action_verbs",
            "tiers": {"preferred": "distinctive but professional; pick openers from here",
                      "overused": "allowed once per OPR, with a warning; avoid 'Led'",
                      "banned": "never used (overused like QB'd, weak/filler, or outlandish)",
                      "neutral": "acceptable"},
            "rules": ["Never reuse an opening verb in Blocks IV-VI; spelled-out and abbreviated forms are the same verb.",
                      "Only approved_forms may be used; unapproved_forms have no approved base abbreviation."],
            "source": "Streamlined from freely shared OPR action-verb lists (verbs by skill; 'game changer' topics). "
                      "The source files are not included.",
            "verbs": out}


def main():
    utf8_stdout()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--glossary-xlsx", action="append", default=[])
    ap.add_argument("--verbs-xlsx", action="append", default=[])
    ap.add_argument("--out", default=str(DATA_DIR))
    args = ap.parse_args()
    if args.glossary_xlsx:
        g = build_glossary(args.glossary_xlsx)
        save_json(Path(args.out) / "glossary.json", g)
        multi = [k for k, v in g["entries"].items() if len(v) > 1]
        print(f"glossary: {len(g['entries'])} short forms; multiple meanings: {', '.join(multi)}")
    if args.verbs_xlsx:
        v = build_verbs(args.verbs_xlsx)
        save_verbs(Path(args.out) / "action_verbs.json", v)
        counts = {}
        for e in v["verbs"]:
            counts[e["tier"]] = counts.get(e["tier"], 0) + 1
        un = sorted({f for e in v["verbs"] for f in e["unapproved_forms"]})
        print(f"verbs: {len(v['verbs'])} {counts}")
        print("unapproved -'d forms:", ", ".join(un))


if __name__ == "__main__":
    main()
